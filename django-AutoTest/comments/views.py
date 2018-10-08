from django.contrib.auth.views import login_required
from django.shortcuts import get_object_or_404, redirect
from .models import CommentModel

@login_required
def delete_own_comment(request, comment_id):
    comment = get_object_or_404(CommentModel, id=comment_id)
    if comment.user == request.user:
        comment.is_removed = True
        comment.save()
    return redirect('blog:diary_detail', comment.object_pk)