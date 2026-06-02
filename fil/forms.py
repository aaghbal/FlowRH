from django import forms
from .models import Poll

class PollForm(forms.ModelForm):
    option1 = forms.CharField(label="Option 1", required=True)
    option2 = forms.CharField(label="Option 2", required=True)
    option3 = forms.CharField(label="Option 3", required=False)
    option4 = forms.CharField(label="Option 4", required=False)

    class Meta:
        model = Poll
        fields = ['question', 'is_multiple_choice', 'duration']
        labels = {
            'question': 'Question',
            'is_multiple_choice': 'Allow multiple votes',
            'duration': 'Duration (days)',
        }

    def save(self, commit=True):
        poll = super().save(commit)
        from .models import PollOption
        for opt in ['option1', 'option2', 'option3', 'option4']:
            value = self.cleaned_data.get(opt)
            if value:
                PollOption.objects.create(poll=poll, option_text=value)
        return poll
