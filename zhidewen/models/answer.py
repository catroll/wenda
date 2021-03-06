#-*- encoding: utf-8 -*-

from django.db import models
from django.utils import timezone
from zhidewen.models import base
from zhidewen.models.question import Question
from zhidewen.models import signals


class AnswerQuerySet(base.QuerySet):

    def best(self):
        return self.order_by('-ranking_weight')

    def oldest(self):
        return self.order_by('created_at')


class AnswerManager(AnswerQuerySet.as_manager()):

    def answer_question(self, user, question, content, **kwargs):
        answer = self.create(content=content, question=question, created_by=user, last_updated_by=user, **kwargs)
        signals.create_content.send(answer.__class__, instance=answer)
        return answer


class Answer(base.ContentModel):
    objects = AnswerManager()
    existed = AnswerManager.existed_manager()

    question = models.ForeignKey(Question, related_name='answers', verbose_name=u'问题')
    content = models.TextField(verbose_name=u'答案')

    class Meta:
        app_label = 'zhidewen'
        db_table = 'zhidewen_answers'

    def count_ranking(self):
        return self.up_count - self.down_count


def create_answer(instance, **kwargs):
    """
    回答问题后的事务：
        回答人的答题次数加一
        问题的回答次数加一，刷新时间更新为当前时间
    """
    instance.created_by.answer_count += 1
    instance.created_by.save()
    instance.question.answer_count += 1
    instance.question.last_refreshed_at = timezone.now()
    instance.question.save()


def delete_answer(instance, **kwargs):
    """
    删除问题后的事务：
        回答人的答题次数减一
        问题的回答次数减一   注意：刷新时间不做更新
    """
    instance.created_by.answer_count -= 1
    instance.created_by.save()
    instance.question.answer_count -= 1
    instance.question.save()


signals.create_content.connect(create_answer, sender=Answer)
signals.delete_content.connect(delete_answer, sender=Answer)
