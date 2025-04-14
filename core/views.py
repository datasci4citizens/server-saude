from django.contrib.auth.decorators import login_required
from django.http import JsonResponse


# Just a test endpoint to check if the user is logged in and return user info
@login_required
def me(request):
    user = request.user
    return JsonResponse(
        {
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
    )
