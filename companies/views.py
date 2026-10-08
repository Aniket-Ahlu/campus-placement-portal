from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from core.decorators import recruiter_required
from .models import Company
from .forms import CompanyForm


@recruiter_required
def company_profile(request):
    """
    Recruiter's view to manage their company profile.
    Shows approval status, rejection reason if any, and allows edit / resubmission.
    """
    company = Company.objects.filter(owner=request.user).first()

    if request.method == 'POST':
        if company:
            form = CompanyForm(request.POST, instance=company)
        else:
            form = CompanyForm(request.POST)

        if form.is_valid():
            inst = form.save(commit=False)
            inst.owner = request.user
            # If company was rejected, editing and saving resubmits for approval
            if inst.status == Company.STATUS_REJECTED:
                inst.status = Company.STATUS_PENDING
                inst.rejection_reason = ''
                messages.info(request, "Company profile resubmitted for admin approval.")
            else:
                messages.success(request, "Company details saved successfully.")
            inst.save()
            return redirect('companies:profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        if company:
            form = CompanyForm(instance=company)
        else:
            form = CompanyForm()

    return render(request, 'companies/company_profile.html', {
        'form': form,
        'company': company,
    })
