from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from board.models import Board

BOARD_NAMES = {
    'notice': '공지사항',
    'community': '커뮤니티',
    'qna': 'Q&A',
}


def _ctx(request):
    """세션에서 로그인 정보와 권한을 꺼내 context dict로 반환."""
    if 'member_no' in request.session:
        return {
            'member_no': request.session['member_no'],
            'member_name': request.session['member_name'],
            'member_role': request.session.get('member_role', 'member'),
        }
    return {'member_no': None, 'member_name': None, 'member_role': None}


def _is_admin(request):
    return request.session.get('member_role') == 'admin'


def _is_logged_in(request):
    return 'member_no' in request.session


def home(request):
    return render(request, 'home.html', _ctx(request))


# ── 게시판 공통 뷰 ────────────────────────────────────────────

def board_list(request, board_type):
    ctx = _ctx(request)
    ctx['board_type'] = board_type
    ctx['board_type_name'] = BOARD_NAMES[board_type]
    ctx['posts'] = Board.objects.filter(board_type=board_type, usage_flag='1', parent_no=0)
    return render(request, 'board_list_new.html', ctx)


def board_write(request, board_type):
    # 공지사항: 관리자만, 커뮤니티/Q&A(질문): 로그인한 회원 누구나
    if not _is_logged_in(request):
        return redirect('/')
    if board_type == 'notice' and not _is_admin(request):
        return redirect('/notice')

    ctx = _ctx(request)
    ctx['board_type'] = board_type
    ctx['board_type_name'] = BOARD_NAMES[board_type]
    ctx['post'] = None
    return render(request, 'board_write_new.html', ctx)


def board_insert(request, board_type):
    if not _is_logged_in(request):
        return redirect('/')
    if board_type == 'notice' and not _is_admin(request):
        return redirect('/notice')

    title = request.POST.get('b_title', '').strip()
    note = request.POST.get('b_note', '').strip()
    writer = request.session['member_name']
    if title:
        Board.objects.create(
            board_type=board_type,
            b_title=title,
            b_note=note,
            b_writer=writer,
        )
    return redirect(f'/{board_type}')


def board_view(request, board_type):
    bno = request.GET.get('b_no')
    post = Board.objects.get(b_no=bno)
    post.b_count += 1
    post.save()

    ctx = _ctx(request)
    ctx['board_type'] = board_type
    ctx['board_type_name'] = BOARD_NAMES[board_type]
    ctx['post'] = post
    if board_type == 'qna':
        ctx['answers'] = Board.objects.filter(parent_no=bno, usage_flag='1').order_by('b_date')
    return render(request, 'board_view_new.html', ctx)


def board_edit(request, board_type):
    if not _is_logged_in(request):
        return redirect('/')
    bno = request.GET.get('b_no')
    post = Board.objects.get(b_no=bno)

    # 본인 글이거나 관리자만 수정 가능
    if post.b_writer != request.session.get('member_name') and not _is_admin(request):
        return redirect(f'/{board_type}/view?b_no={bno}')

    ctx = _ctx(request)
    ctx['board_type'] = board_type
    ctx['board_type_name'] = BOARD_NAMES[board_type]
    ctx['post'] = post
    return render(request, 'board_write_new.html', ctx)


def board_update(request, board_type):
    if not _is_logged_in(request):
        return redirect('/')
    bno = request.POST.get('b_no')
    post = Board.objects.get(b_no=bno)

    if post.b_writer != request.session.get('member_name') and not _is_admin(request):
        return redirect(f'/{board_type}/view?b_no={bno}')

    post.b_title = request.POST.get('b_title', post.b_title).strip() or post.b_title
    post.b_note = request.POST.get('b_note', post.b_note).strip() or post.b_note
    post.save()
    return redirect(f'/{board_type}/view?b_no={bno}')


def board_delete(request, board_type):
    if not _is_logged_in(request):
        return redirect('/')
    bno = request.GET.get('b_no')
    post = Board.objects.get(b_no=bno)

    # 본인 글이거나 관리자만 삭제 가능
    if post.b_writer != request.session.get('member_name') and not _is_admin(request):
        return redirect(f'/{board_type}/view?b_no={bno}')

    post.usage_flag = '0'
    post.save()
    return redirect(f'/{board_type}')


def qna_answer_insert(request):
    # Q&A 답변은 관리자만
    if not _is_admin(request):
        return redirect('/qna')

    parent_no = request.POST.get('parent_no')
    note = request.POST.get('b_note', '').strip()
    writer = request.session['member_name']
    if note and parent_no:
        Board.objects.create(
            board_type='qna',
            b_title='[답변]',
            b_note=note,
            b_writer=writer,
            parent_no=int(parent_no),
        )
    return redirect(f'/qna/view?b_no={parent_no}')


# ── 기존 코드 호환용 ──────────────────────────────────────────

def board(request):
    ctx = _ctx(request)
    if not ctx['member_no']:
        return redirect('/')
    posts = Board.objects.filter(usage_flag='1', parent_no=0)
    return render(request, 'board_list.html', {'rsBoard': posts, **ctx})


def board_ajax(request):
    rsBoard = Board.objects.filter(usage_flag='1', parent_no=0)[:3]
    return render(request, 'board_ajax.html', {'rsBoard': rsBoard})


@csrf_exempt
def board_deleteajax(request):
    bno = request.GET.get('b_no')
    Board.objects.filter(b_no=bno).update(usage_flag='0')
    return JsonResponse({'result_msg': 'Deleted...'})
