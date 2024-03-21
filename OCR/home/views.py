from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from .forms import UploadFileForm
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
import os
from .tasks import run_ocr_on_file  # Importing the specific function


@login_required 
def file_upload(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            myfile = request.FILES['file']
            file_location = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploads'))
            filename = file_location.save(myfile.name, myfile)
            file_path = file_location.path(filename)

            # Run OCR on the uploaded file
            run_ocr_on_file(file_path)


            base, ext = os.path.splitext(filename)
            processed_filename = f"{base}_OCR{ext}"
            processed_file_path = file_location.path(processed_filename)
            try: 
                # Send email with attachment
                send_email_with_attachment(
                    request.user.email,  # Using the logged-in user's email
                    'OCR Document Processed',
                    'Please find your OCR-processed document attached.',
                    processed_file_path
                )
            except: 
                print("Oppsie! Email not configured")
            return redirect('home/file_upload.html')

    else:
        form = UploadFileForm()
    return render(request, 'home/file_upload.html', {'form': form})



def send_email_with_attachment(receiver_email, subject, body, attachment_path):
    email = EmailMessage(
        subject,
        body,
        '',  # Your sender email address
        '',
    )
    email.attach_file(attachment_path)
    email.send()



@login_required
def home(request):
    return render(request, 'home/home.html')
