from django import forms
from django_comments.forms import CommentForm as BaseCommentForm
from django_comments.abstracts import COMMENT_MAX_LENGTH

class CommentForm(BaseCommentForm):
    comment = forms.CharField(label='评论', widget=forms.Textarea(attrs={'class': 'form-control'}), max_length=COMMENT_MAX_LENGTH)

    def get_comment_create_data(self, site_id=None):
        data = super(CommentForm, self).get_comment_create_data(site_id)
        data['comment'] = self.cleaned_data['comment']
        return data