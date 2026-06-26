from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # 공지사항
    path('notice', views.board_list, {'board_type': 'notice'}, name='notice'),
    path('notice/write', views.board_write, {'board_type': 'notice'}, name='notice_write'),
    path('notice/insert', views.board_insert, {'board_type': 'notice'}, name='notice_insert'),
    path('notice/view', views.board_view, {'board_type': 'notice'}, name='notice_view'),
    path('notice/edit', views.board_edit, {'board_type': 'notice'}, name='notice_edit'),
    path('notice/update', views.board_update, {'board_type': 'notice'}, name='notice_update'),
    path('notice/delete', views.board_delete, {'board_type': 'notice'}, name='notice_delete'),

    # 커뮤니티
    path('community', views.board_list, {'board_type': 'community'}, name='community'),
    path('community/write', views.board_write, {'board_type': 'community'}, name='community_write'),
    path('community/insert', views.board_insert, {'board_type': 'community'}, name='community_insert'),
    path('community/view', views.board_view, {'board_type': 'community'}, name='community_view'),
    path('community/edit', views.board_edit, {'board_type': 'community'}, name='community_edit'),
    path('community/update', views.board_update, {'board_type': 'community'}, name='community_update'),
    path('community/delete', views.board_delete, {'board_type': 'community'}, name='community_delete'),

    # Q&A
    path('qna', views.board_list, {'board_type': 'qna'}, name='qna'),
    path('qna/write', views.board_write, {'board_type': 'qna'}, name='qna_write'),
    path('qna/insert', views.board_insert, {'board_type': 'qna'}, name='qna_insert'),
    path('qna/view', views.board_view, {'board_type': 'qna'}, name='qna_view'),
    path('qna/edit', views.board_edit, {'board_type': 'qna'}, name='qna_edit'),
    path('qna/update', views.board_update, {'board_type': 'qna'}, name='qna_update'),
    path('qna/delete', views.board_delete, {'board_type': 'qna'}, name='qna_delete'),
    path('qna/answer', views.qna_answer_insert, name='qna_answer'),

    # 기존 호환
    path('board', views.board, name='board'),
    path('board_ajax', views.board_ajax, name='board_ajax'),
    path('board_deleteajax', views.board_deleteajax, name='board_deleteajax'),
]
