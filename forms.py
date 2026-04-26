from django import forms

class SignUpForm(forms.Form):
    ROLE_CHOICES = (
        ('citizen', 'Citizen'),
        ('policymaker', 'Policymaker'),
        ('corporate_leader', 'Corporate Leader'),
    )

    username = forms.CharField(max_length=100)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=ROLE_CHOICES)


class SignInForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)