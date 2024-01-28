from django.shortcuts import render


# Create your views here.
def dashboard(request):
    context = {
        'running_job': 2,
        'datasource_count': 4,
        'trader_count': 12,
        'strategy_count': 30
    }
    return render(request, 'workstation/dashboard.html', context)
