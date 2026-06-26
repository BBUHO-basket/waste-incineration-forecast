from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from datetime import datetime

from member.models import Member, Suwontrash_all


def member_register(request):
    return render(request, 'member_register.html')
#def 함수이름(필요한정보):
#render(누구에게,무슨화면을,무슨 데이터를 가지)

@csrf_exempt
def member_idcheck(request):
    memberid = request.GET.get('member_id', '')
    exists = Member.objects.filter(member_id=memberid).exists()
    if exists:
        return JsonResponse({'flag': '1', 'result_msg': '이미 사용중인 아이디입니다.'})
    return JsonResponse({'flag': '0', 'result_msg': '사용 가능한 아이디입니다.'})


@csrf_exempt #csrf 보안검사를 생략한다
def member_insert(request):
    memberid = request.GET.get('member_id', '')
    #객체.get(가져올값,없으면 대신 사용할 값)
    memberpwd = request.GET.get('member_pwd', '')
    membername = request.GET.get('member_name', '')
    memberemail = request.GET.get('member_email', '')
    memberfacility = request.GET.get('member_facility', '')

    if not memberid or not memberpwd:
        return JsonResponse({'flag': '1', 'result_msg': '아이디와 비밀번호를 입력하세요.'})
        #{ 키 : 값 }
    if Member.objects.filter(member_id=memberid).exists():
        return JsonResponse({'flag': '1', 'result_msg': '이미 사용중인 아이디입니다.'})

    Member.objects.create(
        member_id=memberid,
        member_pwd=memberpwd,
        member_name=membername,
        member_email=memberemail,
        facility=memberfacility,
    )
    return JsonResponse({'flag': '1', 'result_msg': '회원가입 되었습니다.<br>Home에서 로그인하세요.'})


@csrf_exempt
def member_login(request):
    memberid = request.GET.get('member_id', '')
    memberpwd = request.GET.get('member_pwd', '')

    if 'member_no' in request.session:
        return JsonResponse({'flag': '1', 'result_msg': '이미 로그인 되어 있습니다.'})

    try:
        member = Member.objects.get(member_id=memberid, member_pwd=memberpwd)
        member.access_latest = datetime.now()
        member.save()
        request.session['member_no'] = member.member_no
        request.session['member_name'] = member.member_name
        request.session['member_role'] = member.role
        request.session['member_facility'] = member.facility
        return JsonResponse({'flag': '0', 'result_msg': '로그인 성공'})
    except Member.DoesNotExist:
        return JsonResponse({'flag': '1', 'result_msg': '아이디 또는 비밀번호를 확인하세요.'})


def member_logout(request):
    request.session.flush()
    return redirect('/')


def member_edit(request):
    if 'member_no' not in request.session:
        return redirect('/')

    memberno = request.session['member_no']
    member = Member.objects.get(member_no=memberno)
    context = {
        'member_no': member.member_no,
        'member_id': member.member_id,
        'member_name': member.member_name,
        'member_email': member.member_email,
    }
    return render(request, 'member_edit.html', context)


@csrf_exempt
def member_update(request):
    if 'member_no' not in request.session:
        return JsonResponse({'flag': '1', 'result_msg': '로그인이 필요합니다.'})

    memberno = request.session['member_no']
    member = Member.objects.get(member_no=memberno)
    member.member_name = request.GET.get('member_name', member.member_name)
    member.member_email = request.GET.get('member_email', member.member_email)
    member.save()
    request.session['member_name'] = member.member_name
    return JsonResponse({'flag': '0', 'result_msg': '정보가 변경되었습니다.'})


def trash_input(request):
    return render(request, 'trash_input.html')


def Insertrecord(request):
    if request.method == 'POST':
        if request.POST.get('date') and request.POST.get('total'):
            record = Suwontrash_all()
            record.date = request.POST.get('date')
            record.total = request.POST.get('total')
            record.save()
            messages.success(request, 'Record Saved Successfully!')
    return render(request, 'Index.html')
