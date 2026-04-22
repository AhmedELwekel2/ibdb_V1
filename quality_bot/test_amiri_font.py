import sys
import os
import traceback

# Add project root so imports work
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate

def test_font():
    try:
        # Register Arabic font
        font_path = os.path.join(CURRENT_DIR, 'Amiri-Regular.ttf')
        pdfmetrics.registerFont(TTFont('Amiri', font_path))
        pdfmetrics.registerFont(TTFont('Amiri-Bold', font_path))
        pdfmetrics.registerFont(TTFont('Amiri-Italic', font_path))
        pdfmetrics.registerFont(TTFont('Amiri-BoldItalic', font_path))
        
        # Try both upper and lower case
        registerFontFamily('Amiri', normal='Amiri', bold='Amiri-Bold', italic='Amiri-Italic', boldItalic='Amiri-BoldItalic')
        registerFontFamily('amiri', normal='Amiri', bold='Amiri-Bold', italic='Amiri-Italic', boldItalic='Amiri-BoldItalic')
        
        print("Font registered OK")
        
        styles = getSampleStyleSheet()
        blog_title_style = ParagraphStyle(
            'BlogTitle',
            parent=styles['Normal'],   # The fix I made
            fontName='Amiri',
            fontSize=28
        )
        
        # The crash paragraph
        p = Paragraph("التقرير اليومي للجودة والتميز", blog_title_style)
        
        doc = SimpleDocTemplate("test_output.pdf")
        doc.build([p])
        print("PDF Built OK")
    except Exception as e:
        print("ERROR:", str(e))
        traceback.print_exc()

if __name__ == '__main__':
    test_font()
