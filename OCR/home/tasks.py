import base64
import re
from tempfile import TemporaryDirectory
from math import atan, cos, sin
from typing import Dict, Optional, Tuple
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element
import os
import numpy as np
import PyPDF2
from PyPDF2 import PdfFileMerger
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from PIL import Image
from reportlab.lib.colors import black
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
import fitz
import time
import shutil
from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings

class HocrParser():
    def __init__(self):
        self.box_pattern = re.compile(r'bbox((\s+\d+){4})')
        self.baseline_pattern = re.compile(r'baseline((\s+[\d\.\-]+){2})')

    def _element_coordinates(self, element: Element) -> Dict:

        out = out = {'x1': 0, 'y1': 0, 'x2': 0, 'y2': 0}
        if 'title' in element.attrib:
            matches = self.box_pattern.search(element.attrib['title'])
            if matches:
                coords = matches.group(1).split()
                out = {'x1': int(coords[0]), 'y1': int(
                    coords[1]), 'x2': int(coords[2]), 'y2': int(coords[3])}
        return out

    def _get_baseline(self, element: Element) -> Tuple[float, float]:

        if 'title' in element.attrib:
            matches = self.baseline_pattern.search(
                element.attrib['title']).group(1).split()
            if matches:
                return float(matches[0]), float(matches[1])
        return (0.0, 0.0)

    def _pt_from_pixel(self, pxl: Dict, dpi: int) -> Dict:

        pt = [(c / dpi * inch) for c in pxl.values()]
        return {'x1': pt[0], 'y1': pt[1], 'x2': pt[2], 'y2': pt[3]}

    def _get_element_text(self, element: Element) -> str:

        text = ''
        if element.text is not None:
            text += element.text
        for child in element:
            text += self._get_element_text(child)
        if element.tail is not None:
            text += element.tail
        return text

    def export_pdfa(self,
                    out_filename: str,
                    hocr: ET.ElementTree,
                    image: Optional[np.ndarray] = None,
                    fontname: str = "Times-Roman",
                    fontsize: int = 12,
                    invisible_text: bool = True,
                    add_spaces: bool = True,
                    dpi: int = 300):
        """
        Generates a PDF/A document from a hOCR document.
        """

        width, height = None, None
        for div in hocr.findall(".//div[@class='ocr_page']"):
            coords = self._element_coordinates(div)
            pt_coords = self._pt_from_pixel(coords, dpi)
            width, height = pt_coords['x2'] - \
                            pt_coords['x1'], pt_coords['y2'] - pt_coords['y1']
            break
        if width is None or height is None:
            raise ValueError("Could not determine page size")

        pdf = Canvas(out_filename, pagesize=(width, height), pageCompression=1)

        span_elements = [element for element in hocr.iterfind(".//span")]
        for line in span_elements:
            if 'class' in line.attrib and line.attrib['class'] == 'ocr_line' and line is not None:

                pxl_line_coords = self._element_coordinates(line)
                line_box = self._pt_from_pixel(pxl_line_coords, dpi)

                slope, pxl_intercept = self._get_baseline(line)
                if abs(slope) < 0.005:
                    slope = 0.0
                angle = atan(slope)
                cos_a, sin_a = cos(angle), sin(angle)
                intercept = pxl_intercept / dpi * inch
                baseline_y2 = height - (line_box['y2'] + intercept)

                text = pdf.beginText()
                text.setFont(fontname, fontsize)
                pdf.setFillColor(black)
                if invisible_text:
                    text.setTextRenderMode(3)  # invisible text

                text.setTextTransform(
                    cos_a, -sin_a, sin_a, cos_a, line_box['x1'], baseline_y2)

                elements = line.findall(".//span[@class='ocrx_word']")
                for elem in elements:
                    elemtxt = self._get_element_text(elem).strip()

                    elemtxt = elemtxt.translate(str.maketrans(
                        {'ﬀ': 'ff', 'ﬃ': 'f‌f‌i', 'ﬄ': 'f‌f‌l', 'ﬁ': 'fi', 'ﬂ': 'fl'}))
                    if not elemtxt:
                        continue

                    pxl_coords = self._element_coordinates(elem)
                    box = self._pt_from_pixel(pxl_coords, dpi)
                    if add_spaces:
                        elemtxt += ' '
                        box_width = box['x2'] + pdf.stringWidth(elemtxt, fontname, fontsize) - box['x1']
                    else:
                        box_width = box['x2'] - box['x1']
                    font_width = pdf.stringWidth(elemtxt, fontname, fontsize)

                    cursor = text.getStartOfLine()
                    dx = box['x1'] - cursor[0]
                    dy = baseline_y2 - cursor[1]
                    text.moveCursor(dx, dy)

                    if font_width > 0:
                        text.setHorizScale(100 * box_width / font_width)
                        text.textOut(elemtxt)
                pdf.drawText(text)

        if image is not None:
            pdf.drawImage(ImageReader(Image.fromarray(image)),
                          0, 0, width=width, height=height)
        pdf.save()


#@shared_task()
def is_scanned_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text.strip():
                return False

        return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


#@shared_task()
def process_scanned_pdf(file_path, output_path, model):
    docs = DocumentFile.from_pdf(file_path)
    result = model(docs)
    xml_outputs = result.export_as_xml()

    parser = HocrParser()
    merger = PdfFileMerger()

    with TemporaryDirectory() as tmpdir:
        for i, (xml, img) in enumerate(zip(xml_outputs, docs)):
            tmp_pdf_path = os.path.join(tmpdir, f"{i}.pdf")
            parser.export_pdfa(tmp_pdf_path, hocr=xml[1], image=img)
            merger.append(tmp_pdf_path)

        merger.write(output_path)
        merger.close()

        for attempt in range(3):
            try:
                shutil.rmtree(tmpdir)
                break
            except PermissionError:
                time.sleep(1)


#@shared_task()
def run_ocr_on_file(file_path):
    model = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_vgg16_bn', pretrained=True)
    if file_path.lower().endswith('.pdf') and is_scanned_pdf(file_path):
        print(f"Processing scanned PDF: {os.path.basename(file_path)}")
        output_file = f"{os.path.splitext(file_path)[0]}_OCR.pdf"
        process_scanned_pdf(file_path, output_file, model)
    else:
        print(f"Skipping non-scanned PDF or non-PDF file: {os.path.basename(file_path)}")

@shared_task
def send_email_with_attachment(receiver_email, subject, body, attachment_path):
    try:
        # Create the EmailMessage instance
        email = EmailMessage(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,  # Use Django's default sender email address
            [receiver_email],  # Receiver's email address
        )
        email.attach_file(attachment_path)
        email.send(fail_silently=False)  # Send email asynchronously
    except Exception as e:
        # Handle any errors that occur during email sending
        print(f"An error occurred while sending email: {e}")





@shared_task
def process_uploaded_file(user_email, uploaded_file):
    # Process the uploaded file (e.g., run OCR)
    file_path = run_ocr_on_file(uploaded_file)

    # Send email with attachment
    send_email_with_attachment(user_email, 'OCR Document Processed',
                               'Please find your OCR-processed document attached.',
                               file_path)
