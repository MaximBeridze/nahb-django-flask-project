from django import forms

class StoryForm(forms.Form):
    title = forms.CharField(max_length=200)
    description = forms.CharField(widget=forms.Textarea, required=False)
    status = forms.ChoiceField(choices=[("draft","draft"),("published","published"),("suspended","suspended")])
    illustration_url = forms.URLField(required=False)

class PageForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea)
    is_ending = forms.BooleanField(required=False)
    ending_label = forms.CharField(max_length=120, required=False)
    illustration_url = forms.URLField(required=False)

class ChoiceForm(forms.Form):
    text = forms.CharField(max_length=240)
    next_page_id = forms.IntegerField()

class RatingForm(forms.Form):
    stars = forms.IntegerField(min_value=1, max_value=5)
    comment = forms.CharField(widget=forms.Textarea, required=False)

class ReportForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea)
