from django.db import models


class Board(models.Model):
    BOARD_TYPES = [
        ('notice', '공지사항'),
        ('community', '커뮤니티'),
        ('qna', 'Q&A'),
    ]

    b_no = models.AutoField(db_column='b_no', primary_key=True)
    board_type = models.CharField(db_column='board_type', max_length=20, choices=BOARD_TYPES, default='community')
    b_title = models.CharField(db_column='b_title', max_length=255)
    b_note = models.TextField(db_column='b_note')
    b_writer = models.CharField(db_column='b_writer', max_length=50)
    parent_no = models.IntegerField(db_column='parent_no', default=0)
    b_count = models.IntegerField(db_column='b_count', default=0)
    b_date = models.DateTimeField(db_column='b_date', auto_now_add=True)
    usage_flag = models.CharField(db_column='usage_flag', max_length=10, default='1')

    class Meta:
        managed = True
        db_table = 'board'
        ordering = ['-b_date']

    def __str__(self):
        return f'[{self.get_board_type_display()}] {self.b_title}'
