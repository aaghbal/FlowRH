
const driver = window.driver.js.driver;



var steps = [
    { popover: { title: 'Tableau de bord', description: 'Section tableau de bord M-Community' } },
    { element: '#attendance-activity-container', popover: { title: 'Pointer la présence', description: 'Utilisé pour pointer votre présence' } },
];

if ($('#settingsMenu').length) {
    steps.push({ element: '#settingsMenu', popover: { title: 'Paramètres', description: 'Configurations des paramètres' } });
}

if ($('#notificationIcon').length) {
    steps.push({ element: '#notificationIcon', popover: { title: 'Notification', description: 'Section des notifications' } });
}

if ($('#multiLanguage').length) {
    steps.push({ element: '#multiLanguage', popover: { title: 'Langue', description: 'Options multilingues' } });
}
if ($('#multCompany').length) {
    steps.push({ element: '#multCompany', popover: { title: 'Multi-entreprise', description: 'Options multi-entreprise' } });
}
if ($('#mainNavProfile').length) {
    steps.push({ element: '#mainNavProfile', popover: { title: 'Profil', description: 'Options de profil et de changement de mot de passe' } });
}
if ($('.oh-card-dashboard').length) {
    steps.push({ element: '#tileContainer .oh-card-dashboard:nth-child(1)', popover: { title: 'Tuiles du tableau de bord', description: 'Tuiles du tableau de bord M-Community' } });
}
setTimeout(() => {
    if ($('.oh-btn-group').length) {
        steps.push({ element: '.oh-btn-group:nth-child(1)', popover: { title: 'Actions du tableau de bord', description: 'Options d\'approbation ou de rejet' } });
    }
    if ($('#addAnnouncement').length) {
        steps.push({ element: '#addAnnouncement', popover: { title: 'Ajouter une annonce', description: 'Créer une annonce depuis le tableau de bord' } });
    }
    if ($('#quickActions').length) {
        steps.push({ element: '#quickActions', popover: { title: 'Actions rapides', description: 'Créer des demandes rapides' } });
    }
    if ($('.oh-sidebar__company').length) {
        steps.push({ element: '.oh-sidebar__company:nth-child(1)', popover: { title: 'Entreprise', description: 'Votre accès à l\'entreprise actuelle' } });
    }
    if ($('[data-id="dashboardNav"]').length) {
        steps.push({ element: '[data-id="dashboardNav"]', popover: { title: 'Application', description: 'Applications RH M-Community. ex : Tableau de bord' } });
    }
}, 1000);
driverObj = driver(

    {
        showProgress: false,
        animate: true,
        showButtons: ['next', 'previous', 'close'],
        steps: steps,


    }
)



function runDriver() {
    // Start driving after checking all steps

    driverObj.drive();
    $.ajax({
        type: "get",
        url: "/driver-viewed?user=" + $(".logged-in[data-user-id]").attr("data-user-id") + "&viewed=dashboard",
        success: function (response) {

        }
    });
}
