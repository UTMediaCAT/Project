from django.shortcuts import render, redirect
from django.template import RequestContext, loader
from subprocess import Popen
import sys, os, datetime, time, re

path = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '../../', 'src'))
sys.path.append(path)
import analyzer
import Caching

def notAvailable(request):
    if not request.user.is_authenticated():
        return redirect('/admin/login/?next=%s' % request.path)

    return render(request, 'statistics/notAvailable.html')
