"""
models.py

This module is used to register models for onboarding app

"""

from datetime import datetime

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from employee.models import Employee
from horilla.models import HorillaModel
from horilla_audit.models import HorillaAuditInfo, HorillaAuditLog
from recruitment.models import Candidate, Recruitment


class OnboardingStage(HorillaModel):
    """
    OnboardingStage models
    """

    stage_title = models.CharField(max_length=200)
    recruitment_id = models.ForeignKey(
        Recruitment,
        verbose_name=_("Recruitment"),
        null=True,
        related_name="onboarding_stage",
        on_delete=models.CASCADE,
    )
    employee_id = models.ManyToManyField(Employee, verbose_name="Stage managers")
    sequence = models.IntegerField(null=True)
    is_final_stage = models.BooleanField(default=False)
    objects = HorillaCompanyManager("recruitment_id__company_id")

    def __str__(self):
        return f"{self.stage_title}"

    class Meta:
        """
        Meta class for additional options
        """

        ordering = ["sequence"]


@receiver(post_save, sender=Recruitment)
def create_initial_stage(sender, instance, created, raw=False, **kwargs):
    """
    This is post save method, used to create initial stage for the recruitment

    `raw` is set while loaddata installs a fixture, which carries its own
    OnboardingStage rows; creating the defaults then would duplicate them.
    """
    if raw:
        return
    if created or not instance.onboarding_stage.first():
        default_stages = [
            (
                "Lettre d'engagement",
                "Remettre la lettre signée, obtenir l'accusé de réception et communiquer les pièces à fournir.",
                False,
            ),
            (
                "Planning d'intégration",
                "Établir le planning et le faire valider par le responsable hiérarchique (J-10 minimum).",
                False,
            ),
            (
                "Préparation administrative",
                "Préparer le contrat (AGIRH), planifier la visite médicale et procéder à l'adhésion assurance.",
                False,
            ),
            (
                "Récupération contrat DG & VS",
                "Récupérer le contrat signé auprès de la Direction Générale et Vice-Secrétaire, et vérifier sa conformité.",
                False,
            ),
            (
                "Préparation SI & matériel",
                "Créer les accès (email, session, CRM, badge) et préparer PC, téléphone, SIM et matériel.",
                False,
            ),
            (
                "Annonce de l'arrivée",
                "Informer le manager puis annoncer l'arrivée au CODIR / CODIR élargi (J-2).",
                False,
            ),
            (
                "Welcome Day",
                "Accueillir, remettre le kit, le contrat et le matériel (bon de remise signé), puis présenter l'entreprise, la Vision DG, la culture ONE-M et le Code de conduite.",
                False,
            ),
            (
                "Intégration métier",
                "Présenter le périmètre, les missions, les interlocuteurs et les outils, et assurer la formation métier.",
                False,
            ),
            (
                "Suivi période d'essai",
                "Transmettre la fiche de titularisation (J-15) et réaliser les points de suivi formalisés.",
                False,
            ),
            (
                "Validation finale",
                "Feedback RH, survey expérience collaborateur et confirmation / renouvellement / non-validation.",
                True,
            ),
        ]
        for seq, (title, task_title, is_final) in enumerate(default_stages):
            stage = OnboardingStage.objects.create(
                recruitment_id=instance,
                stage_title=title,
                sequence=seq,
                is_final_stage=is_final,
            )
            OnboardingTask.objects.create(
                stage_id=stage,
                task_title=task_title,
            )


class OnboardingTask(HorillaModel):
    """
    OnboardingTask models
    """

    task_title = models.CharField(max_length=200)
    # recruitment_id = models.ManyToManyField(Recruitment, related_name="onboarding_task")
    stage_id = models.ForeignKey(
        OnboardingStage,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="onboarding_task",
    )
    candidates = models.ManyToManyField(
        Candidate,
        blank=True,
        related_name="cand_onboarding_task",
    )
    employee_id = models.ManyToManyField(
        Employee, related_name="onboarding_task", verbose_name=_("Task Managers")
    )

    objects = HorillaCompanyManager("stage_id__recruitment_id__company_id")

    def __str__(self):
        return f"{self.task_title}"


class CandidateStage(HorillaModel):
    """
    CandidateStage model
    """

    candidate_id = models.OneToOneField(
        Candidate, on_delete=models.PROTECT, related_name="onboarding_stage"
    )
    onboarding_stage_id = models.ForeignKey(
        OnboardingStage, on_delete=models.PROTECT, related_name="candidate"
    )
    onboarding_end_date = models.DateField(blank=True, null=True)
    sequence = models.IntegerField(null=True, default=0)
    objects = HorillaCompanyManager("candidate_id__recruitment_id__company_id")

    def __str__(self):
        return f"{self.candidate_id}  |  {self.onboarding_stage_id}"

    def save(self, *args, **kwargs):
        if self.onboarding_stage_id.is_final_stage:
            self.onboarding_end_date = datetime.today()
        super(CandidateStage, self).save(*args, **kwargs)

    def task_completion_ratio(self):
        """
        function that used for getting the numbers between task completed v/s tasks assigned
        """
        cans_tasks = self.candidate_id.candidate_task.all()
        completed_tasks = sum(1 for task in cans_tasks if task.status == "done")
        return f"{completed_tasks}/{len(cans_tasks)}"

    class Meta:
        """
        Meta class for additional options
        """

        verbose_name = _("Candidate Onboarding stage")
        ordering = ["sequence"]


class CandidateTask(HorillaModel):
    """
    CandidateTask model
    """

    choice = (
        ("todo", _("À faire")),
        ("scheduled", _("Planifié")),
        ("ongoing", _("En cours")),
        ("stuck", _("Bloqué")),
        ("done", _("Terminé")),
    )
    candidate_id = models.ForeignKey(
        Candidate, on_delete=models.PROTECT, related_name="candidate_task"
    )
    # managers = models.ManyToManyField(Employee)
    stage_id = models.ForeignKey(
        OnboardingStage,
        null=True,
        on_delete=models.PROTECT,
        related_name="candidate_task",
    )
    status = models.CharField(
        max_length=50, choices=choice, blank=True, null=True, default="todo"
    )
    onboarding_task_id = models.ForeignKey(OnboardingTask, on_delete=models.PROTECT)
    objects = HorillaCompanyManager("candidate_id__recruitment_id__company_id")
    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )

    def __str__(self):
        return f"{self.candidate_id}|{self.onboarding_task_id}"

    class Meta:
        """
        Meta class to add some additional options
        """

        verbose_name = _("Candidate onboarding task")
        # unique_together = ("candidate_id", "onboarding_task_id")


class OnboardingPortal(HorillaModel):
    """
    OnboardingPortal model
    """

    candidate_id = models.OneToOneField(
        Candidate, on_delete=models.PROTECT, related_name="onboarding_portal"
    )
    token = models.CharField(max_length=200)
    used = models.BooleanField(default=False)
    count = models.IntegerField(default=0)
    profile = models.ImageField(upload_to="employee/profile", null=True, blank=True)
    objects = HorillaCompanyManager("candidate_id__recruitment_id__company_id")

    def __str__(self):
        return f"{self.candidate_id} | {self.token}"
