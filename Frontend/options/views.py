from django.shortcuts import render, redirect
from django.template import RequestContext, loader
from django.core import management
from django.conf import settings
from django.core.files.storage import default_storage
from subprocess import Popen
import sys, os
import tempfile
from io import StringIO
import common
import json
import urllib.parse
sys.path.insert(0, '../src/excel_to_json_script')

from excel_to_json_script.articles_conversion_script import convert_articles_to_json
from excel_to_json_script.twitter_handles_conversion_script import convert_twitter_handles_to_json

from explorer.models import (
    ReferringSite,
    ReferringSiteFilter,
    ReferringSiteCssSelector,
    ReferringTwitter,
    SourceTwitter,
    SourceTwitterAlias,
    SourceSite,
    SourceSiteAlias,
    Keyword
)
from taggit.models import (
    Tag,
    TaggedItem
)

ALLOWED_EXTENSIONS_JSON = set(['json'])
ALLOWED_EXTENSIONS_EXCEL = set(['xlsx'])

def downloadPage(request):
    if not request.user.is_authenticated():
        return redirect('/admin/login/?next=%s' % request.path)

    return render(request, 'options/downloads.html')

def downloads(request):
    if not request.user.is_authenticated():
        return redirect('/admin/login/?next=%s' % request.path)

    deleted = False
    context = {}
    if request.method == 'POST':
        try:
            scopefile = request.FILES['scopefile']
            try:
                version = scopefile.readline().strip()
                db_version = common.get_config()['database']['version']
                if (str(version.count(bytes('.'.encode('utf-8')))) == 2 and version != db_version):
                    result = format("Database schema version mismatch (Need: %s, Given: %s)" %
                                    (db_version, version))
                else:
                    # Backup Current Scope in a variable
                    out = StringIO()
                    management.call_command('dumpdata', 'explorer', 'taggit', stdout=out)
                    currentScope = out.getvalue()
                    out.close()
                    
                    # Delete Current Scope
                    deleteAllScope()
                    deleted = True

                    # Replace Scope
                    tf = tempfile.NamedTemporaryFile(suffix='.json')
                    tf.write(bytes(scopefile.read()))
                    tf.seek(0)
                    out = StringIO()
                    management.call_command('loaddata', tf.name, stdout=out)
                    out.close()
                    tf.close()
                    result = "Success"
            except:
                result = "Failed"
                restoreLastScope(deleted, currentScope)
            finally:
                context['scope_message'] = result
        except:
            pass
    
    return render(request, 'options/downloads.html', context)

def downloadsExcel(request):
    if not request.user.is_authenticated():
        return redirect('/admin/login/?next=%s' % request.path)

    deleted = False
    context = {}
    if request.method == 'POST':
        try:   # upload excel scope file
            scopefile = request.FILES['scopefileExcel']
            selected_type = request.POST['uploadType']
            try:
                # convert excel to json
                # call function to get json file
                save_path = os.path.join(settings.MEDIA_ROOT, 'uploads', scopefile.name)
                file_name = default_storage.save(save_path, scopefile)
                path = default_storage.url(file_name)
                abspath = urllib.parse.unquote(default_storage.path(path))
                convert_articles_to_json(abspath)

                # Backup Current Scope in a variable
                out = StringIO()
                management.call_command('dumpdata', 'explorer', 'taggit', stdout=out)
                currentScope = out.getvalue()
                out.close()

                jsonDict = ""
                articles_jsonfile_path = "/root/Voyage/Frontend/articles.json"
                with open(articles_jsonfile_path) as jsonfile:
                    jsonDict = json.load(jsonfile)
                jsonfile.close()
                # remove newly added files
                os.remove(articles_jsonfile_path)
                os.remove(abspath)

                # read json file one by one
                # context['scope_message_excel'] = jsonDict
                result = ""
                skipped = []
                i = 0
                temp = []

                if (selected_type == "replace"):
                    # Delete Current Scope
                    deleteScopeSite()
                    deleted = True

                    # check if it's in source
                    for type in jsonDict.keys():
                        if "source" in type.lower():
                            # for every obj, add into source site db
                            src = jsonDict[type]
                            for srcgroup in src.keys():
                                obj = src[srcgroup]
                                for eachobj in obj:
                                    i = i + 1
                                    website = eachobj["Website"]
                                    sitename = eachobj["Outlet Name"]
                                    # newstype = obj["Type"]

                                    try:
                                        # add to source
                                        s = SourceSite(url=website, name=sitename)
                                        s.save()
                                        # add tag
                                        s.tags.add(srcgroup)
                                    except:
                                        skipped.append(i)
                            
                        elif "referring" in type.lower():
                            # for every obj, add into referring site db
                            src = jsonDict[type]
                            for srcgroup in src.keys():
                                obj = src[srcgroup]
                                for eachobj in obj:
                                    i = i + 1
                                    website = eachobj["Website"]
                                    sitename = eachobj["Outlet Name"]
                                    default_scan = 2

                                    try:
                                        # add to referring
                                        r = ReferringSite(url=website, name=sitename, mode=default_scan, is_shallow=False)
                                        r.save()
                                        # add tag
                                        r.tags.add(srcgroup)
                                    except:
                                        skipped.append(i)

                    result = "Successfully replaced"
                    if (len(skipped) > 0):
                        result += ", with skipped record of line "
                        result += str(skipped)

                elif (selected_type == "append"):
                    skippedException = []
                    # get info to insert to scope
                    for type in jsonDict.keys():
                        if "source" in type.lower():
                            # for every obj, add into source site db
                            src = jsonDict[type]
                            for srcgroup in src.keys():
                                obj = src[srcgroup]
                                for eachobj in obj:
                                    i = i + 1
                                    website = eachobj["Website"]
                                    sitename = eachobj["Outlet Name"]
                                    try:
                                        try:
                                            SourceSite.objects.get(url=website)
                                            skipped.append(i)
                                        except SourceSite.DoesNotExist:
                                            # add if does not exist
                                            s = SourceSite(url=website, name=sitename)
                                            s.save()
                                            s.tags.add(srcgroup)
                                    except:
                                        skippedException.append(i)

                        elif "referring" in type.lower():
                            # for every obj, add into referring site db
                            src = jsonDict[type]
                            for srcgroup in src.keys():
                                obj = src[srcgroup]
                                for eachobj in obj:
                                    i = i + 1
                                    website = eachobj["Website"]
                                    sitename = eachobj["Outlet Name"]
                                    default_scan = 2 # both scan
                                    try:
                                        try:
                                            ReferringSite.objects.get(url=website)
                                            skipped.append(i)
                                        except ReferringSite.DoesNotExist:
                                            # add if does not exist
                                            r = ReferringSite(url=website, name=sitename, mode=default_scan, is_shallow=False)
                                            r.save()
                                            r.tags.add(srcgroup)
                                    except:
                                        skippedException.append(i)

                    result = "Successfully appended"
                    if (len(skipped) > 0):
                        result += ", with duplicated skipped website of line "
                        result += str(skipped)
                    if (len(skippedException) > 0):
                        result += " , with error occurred skipped website of line "
                        result += str(skippedException)

            # except ValueError as e:
            #     result = "Wrong file type"
            except Exception as e:
                result = "Failed "
                result += str(e)
                restoreLastScope(currentScope)

            finally:
                context['scope_message_excel'] = result
        except:
            pass

    return render(request, 'options/downloads.html', context)

def uploadExcelTwitter(request):
    if not request.user.is_authenticated():
        return redirect('/admin/login/?next=%s' % request.path)

    deleted = False
    context = {}
    if request.method == 'POST':
        try:   # upload excel scope file
            scopefile = request.FILES['scopefileExcelTwitter']
            selected_type = request.POST['uploadType']
            wrong_input = None
            try:
                # convert excel to json
                # call function to get json file
                save_path = os.path.join(settings.MEDIA_ROOT, 'uploads', scopefile.name)
                file_name = default_storage.save(save_path, scopefile)
                path = default_storage.url(file_name)
                abspath = urllib.parse.unquote(default_storage.path(path))
                convert_twitter_handles_to_json(abspath)

                # Backup Current Scope in a variable
                out = StringIO()
                management.call_command('dumpdata', 'explorer.sourcetwitter', 'explorer.sourcetwitteralias', 'explorer.referringtwitter', 'taggit', stdout=out)           # ?????????????????????
                currentScope = out.getvalue()
                out.close()

                jsonDict = ""
                twitter_jsonfile_path = "/root/Voyage/Frontend/twitter_handles.json"
                with open(twitter_jsonfile_path) as jsonfile:
                    jsonDict = json.load(jsonfile)
                jsonfile.close()
                # remove newly added files
                # os.remove(twitter_jsonfile_path)
                os.remove(abspath)

                # read json file one by one
                result = ""
                skipped = []
                skippedException = []
                skippedExceptionExcelEntry = []
                i = 0
                temp = []

                if (selected_type == "replace"):
                    # Delete Current Scope
                    deleteScopeTwitter()
                    deleted = True

                    # check if it's in source
                    for eachdomain in jsonDict.keys():
                            # for every obj, add into source site db
                            domainObj = jsonDict[eachdomain]

                            # objarr = [twitterName, twitterHandle, type, domain]
                            for eachTwitterObj in domainObj:
                                i = i + 1
                                objdict = getTwitterAttributes(eachTwitterObj)
                                wrong_input = objdict['twitterName']

                                # if belongs to source
                                if "source" in objdict['type'].lower():
                                    try:
                                        # add to source
                                        s1 = SourceTwitter(name=objdict['twitterHandle'])
                                        s1.save()
                                        # get foreign key for SourceTwitterAlias
                                        fk = SourceTwitter.objects.get(name=objdict['twitterHandle'])
                                        s2 = SourceTwitterAlias(primary=fk, alias=objdict['twitterName'])
                                        s2.save()
                                        # maybe add tag (from which domain)
                                        s1.tags.add(eachdomain)
                                    except:
                                        skipped.append(i)
                                elif "referring" in objdict['type'].lower():
                                    try:
                                        # add to referring
                                        r1 = ReferringTwitter(name=objdict['twitterHandle'])
                                        r1.save()
                                        # maybe add tag (from which domain)
                                        r1.tags.add(eachdomain)
                                    except:
                                        skipped.append(i)

                    result = "Successfully replaced"
                    if (len(skipped) > 0):
                        result += ", with skipped record of line "
                        result += str(skipped)
            
                elif (selected_type == "append"):
                    for eachdomain in jsonDict.keys():
                        # for every obj, add into source site db
                        domainObj = jsonDict[eachdomain]
                        for eachTwitterObj in domainObj:
                            i = i + 1
                            objdict = getTwitterAttributes(eachTwitterObj)
                            if (objdict == -1):
                                result += "0 "
                                # skippedExceptionExcelEntry.append(eachTwitterObj)
                                continue
                                # raise Exception()

                            # if belongs to source
                            if "source" in objdict['type'].lower():    
                                try:
                                    try:
                                        # add only if twitter handle not exist
                                        SourceTwitter.objects.get(name=objdict['twitterHandle'])
                                        skipped.append(i)
                                    except SourceTwitter.DoesNotExist:
                                        # add to source
                                        s1 = SourceTwitter(name=objdict['twitterHandle'])
                                        s1.save()
                                        # get foreign key for SourceTwitterAlias
                                        fk = SourceTwitter.objects.get(name=objdict['twitterHandle'])
                                        s2 = SourceTwitterAlias(primary=fk, alias=objdict['twitterName'])
                                        s2.save()
                                        # maybe add tag (from which domain)
                                        s1.tags.add(eachdomain)
                                except Exception as e:
                                    result += "1 "
                                    result += str(e)
                                    skippedException.append(i)
                            elif "referring" in objdict['type'].lower():
                                try:
                                    try:
                                        ReferringTwitter.objects.get(name=objdict['twitterHandle'])
                                        skipped.append(i)
                                    except ReferringTwitter.DoesNotExist:
                                        # add to referring
                                        r1 = ReferringTwitter(name=objdict['twitterHandle'])
                                        r1.save()
                                        # maybe add tag (from which domain)
                                        r1.tags.add(eachdomain)
                                except Exception as e:
                                    result += "2 "
                                    result += str(e)
                                    skippedException.append(i)

                    result = "Successfully appened"
                    if (len(skipped) > 0):
                        result += ", with duplicated skipped twitter of line "
                        result += str(skipped)
                    if (len(skippedException) > 0):
                        result += " , with error occurred skipped twitter of line "
                        result += str(skippedException)
                    if (len(skippedExceptionExcelEntry) > 0):
                        result += " , with error occurred in excel skipped twitter of line "
                        result += str(skippedExceptionExcelEntry)

            # except ValueError as e:
            #     result = "Wrong file type"
            except Exception as e:
                # TODO: if replace, remove all entered data, restore old scope
                # else remain


                result += "Failed Twitter: "
                result += str(e)
                if (wrong_input != None):
                    result = result + ", wrong header or record on Twitter Name: " + wrong_input
                # result="sth wrong"
                restoreLastScope(currentScope)

            finally:
                context['scope_message_exceltwitter'] = result
        except:
            pass

    return render(request, 'options/downloads.html', context)

def getTwitterAttributes(eachTwitterObj):
    result = {}
    if checkTwitterFields(eachTwitterObj) :
        return -1

    twitterName = eachTwitterObj["Name"].strip()    
    twitterHandle = eachTwitterObj["Twitter Handle"].strip()
    type = eachTwitterObj["Source/Referring"].strip()
    # domain = eachTwitterObj["Domain"].strip()
    # remove '@' if exist
    if (twitterHandle[0] == '@'):
        twitterHandle = twitterHandle[1:]

    # result['domain'] = domain
    result['twitterName'] = twitterName
    result['twitterHandle'] = twitterHandle
    result['type'] = type
        
    return result

def checkTwitterFields(obj):
    incomplete = 0
    if (obj['Twitter Handle'] == None):
        incomplete = 1
    # if (obj['Domain'] == None):
    #     incomplete = 1
    if (obj['Name'] == None):
        incomplete = 1
    if (obj['Source/Referring'] == None):
        incomplete = 1
    return incomplete


def deleteAllScope():
    ReferringSite.objects.all().delete()
    ReferringSiteFilter.objects.all().delete()
    ReferringSiteCssSelector.objects.all().delete()
    ReferringTwitter.objects.all().delete()
    SourceTwitter.objects.all().delete()
    SourceTwitterAlias.objects.all().delete()
    SourceSite.objects.all().delete()
    SourceSiteAlias.objects.all().delete()
    Keyword.objects.all().delete()
    Tag.objects.all().delete()
    TaggedItem.objects.all().delete()

def deleteScopeSite():
    ReferringSite.objects.all().delete()
    ReferringSiteFilter.objects.all().delete()
    SourceSite.objects.all().delete()
    SourceSiteAlias.objects.all().delete()
    # Keyword.objects.all().delete()
    # Tag.objects.all().delete()
    # TaggedItem.objects.all().delete()

def deleteScopeTwitter():
    ReferringSiteCssSelector.objects.all().delete()
    ReferringTwitter.objects.all().delete()
    SourceTwitter.objects.all().delete()
    SourceTwitterAlias.objects.all().delete()
    # Keyword.objects.all().delete()
    # Tag.objects.all().delete()
    # TaggedItem.objects.all().delete()

def restoreLastScope(currentScope):
    # if (deleted):
    # Put the Current Scope back into db
    tf = tempfile.NamedTemporaryFile('w+t', suffix='.json')
    try:
        with open(tf.name, 'w') as fd:
            fd.write(currentScope)
            fd.seek(0)
            management.call_command('loaddata', tf.name)
    finally:
        tf.close()

def allowed_file(filename, allowlist):
    return filename.split('.', 1)[1].lower() in allowlist
