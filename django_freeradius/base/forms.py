import re

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import ugettext_lazy as _

from .. import settings as app_settings
from .models import RADCHECK_PASSWD_TYPE, AbstractNas, AbstractRadiusCheck

radcheck_value_field = AbstractRadiusCheck._meta.get_field('value')
nas_type_field = AbstractNas._meta.get_field('type')


class ModeSwitcherForm(forms.ModelForm):
    MODE_CHOICES = (
        ('-', '----- {0} -----'.format(_('Please select an option'))),
        ('guided', _('Guided (dropdown)')),
        ('custom', _('Custom (text input)'))
    )
    mode = forms.ChoiceField(choices=MODE_CHOICES)

    class Media:
        js = ('django-freeradius/js/mode-switcher.js',)
        css = {'all': ('django-freeradius/css/mode-switcher.css',)}


class RadiusCheckForm(ModeSwitcherForm):
    _secret_help_text = _('The secret must contain at least one lowercase '
                          'and uppercase characters, '
                          'one number and one of these symbols: '
                          '! % - _ + = [ ] { } : , . ? < > ( ) ; ')
    # custom field not backed by database
    new_value = forms.CharField(label=_('Value'), required=False,
                                max_length=radcheck_value_field.max_length,
                                widget=forms.PasswordInput(),)

    def clean_attribute(self):
        if self.data['attribute'] not in app_settings.DISABLED_SECRET_FORMATS:
            return self.cleaned_data['attribute']

    def clean_new_value(self):
        if not self.data['new_value']:
            return None
        if self.data['attribute'] in RADCHECK_PASSWD_TYPE:
            for regexp in app_settings.RADCHECK_SECRET_VALIDATORS.values():
                found = re.findall(regexp, self.data['new_value'])
                if not found:
                    raise ValidationError(self._secret_help_text)
        return self.cleaned_data['new_value']

    class Media:
        js = ('django-freeradius/js/radcheck.js',)
        css = {'all': ('django-freeradius/css/radcheck.css',)}


class RadiusBatchForm(forms.ModelForm):
    number_of_users = forms.IntegerField(required=False,
                                         validators=[MinValueValidator(1)],
                                         help_text=_('Number of users to be generated'))

    def clean(self):
        data = self.cleaned_data
        strategy = data.get('strategy')
        number_of_users = data.get('number_of_users')
        if strategy == 'prefix' and not number_of_users:
            self.add_error('number_of_users', 'This field is required')
        return data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'csvfile' in self.fields:
            docs_link = "https://django-freeradius.readthedocs.io/en/latest/general/importing_users.html"
            help_text = "Refer to the <b><u><a href='{}'>docs</a></u></b> for more \
                details on importing users from a CSV".format(docs_link)
            self.fields['csvfile'].help_text = help_text
