from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponseServerError
from django.core.urlresolvers import reverse
from django.utils.timezone import now
from django.views.generic.edit import FormView

from pttrack.views import NoteFormView, NoteUpdate, get_current_provider_type
from pttrack.models import Patient, ProviderType

from . import models
from . import forms

def get_clindates():
    '''Get the clinic dates associated with today.'''
    clindates = models.ClinicDate.objects.filter(
        clinic_date=now().date())
    return clindates


class WorkupCreate(NoteFormView):
    '''A view for creating a new workup. Checks to see if today is a
    clinic date first, and prompts its creation if none exist.'''
    template_name = 'workup/workup-create.html'
    form_class = forms.WorkupForm
    note_type = 'Workup'

    def get(self, *args, **kwargs):
        """Check that we have an instantiated ClinicDate today,
        then dispatch to get() of the superclass view."""

        clindates = get_clindates()
        pt = get_object_or_404(Patient, pk=kwargs['pt_id'])

        if len(clindates) == 0:
            # dispatch to ClinicDateCreate because the ClinicDate doesn't exist
            return HttpResponseRedirect(reverse("new-clindate", args=(pt.id,)))
        elif len(clindates) == 1:
            # dispatch to our own view, since we know there's a ClinicDate
            # for today
            kwargs['pt_id'] = pt.id
            return super(WorkupCreate,
                         self).get(self, *args, **kwargs)
        else:  # we have >1 clindate today.
            return HttpResponseServerError("<h3>We don't know how to handle " +
                                           ">1 clinic day on a particular " +
                                           "day!</h3>")

    def form_valid(self, form):
        pt = get_object_or_404(Patient, pk=self.kwargs['pt_id'])
        active_provider_type = get_object_or_404(
            ProviderType,
            pk=self.request.session['clintype_pk'])

        wu = form.save(commit=False)
        wu.patient = pt
        wu.author = self.request.user.provider
        wu.author_type = get_current_provider_type(self.request)
        wu.clinic_day = get_clindates()[0]
        if wu.author_type.signs_charts:
            wu.sign(self.request.user, active_provider_type)

        wu.save()

        form.save_m2m()

        return HttpResponseRedirect(reverse("new-action-item", args=(pt.id,)))


class WorkupUpdate(NoteUpdate):
    template_name = "pttrack/form-update.html"
    model = models.Workup
    form_class = forms.WorkupForm
    note_type = "Workup"

    def dispatch(self, *args, **kwargs):
        '''
        Intercept dispatch for NoteUpdate and verify that the user has 
        permission to modify this Workup.
        '''
        current_user_type = get_current_provider_type(self.request)
        wu = get_object_or_404(models.Workup, pk=kwargs['pk'])

        # if it's an attending, we allow updates.
        if current_user_type.signs_charts or not wu.signed():
            return super(NoteUpdate, self).dispatch(*args, **kwargs)
        else:
            return HttpResponseRedirect(reverse('workup',
                                        args=(kwargs['pk'],)))


class ClinicDateCreate(FormView):
    '''A view for creating a new ClinicDate. On submission, it redirects to
    the new-workup view.'''
    template_name = 'pttrack/clindate.html'
    form_class = forms.ClinicDateForm

    def form_valid(self, form):
        '''Update clinic day's internal date.'''
        clindate = form.save(commit=False)

        today = now().date()
        clindate.clinic_date = today
        clindate.save()

        # determine from our URL which patient we wanted to work up before we
        # got redirected to create a clinic date

        pt = get_object_or_404(Patient, pk=self.kwargs['pt_id'])
        return HttpResponseRedirect(reverse("new-workup", args=(pt.id,)))


def sign_workup(request, pk):

    wu = get_object_or_404(models.Workup, pk=pk)
    active_provider_type = get_object_or_404(ProviderType,
                                             pk=request.session['clintype_pk'])

    try:
        wu.sign(request.user, active_provider_type)
        wu.save()
    except ValueError:
        # thrown exception can be ignored since we just redirect back to the 
        # workup detail view anyway
        pass

    return HttpResponseRedirect(reverse("workup", args=(wu.id,)))


def error_workup(request, pk):

    wu = get_object_or_404(models.Workup, pk=pk)

    #TODO: clearly a template error here.
    return render(request, 'pttrack/workup_error.html', {'workup': wu})
