from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch

def create_demo_pdf():
    """Create a demo PDF for testing the voice accessibility app"""
    
    # Read the demo content
    with open('demo_content.txt', 'r') as f:
        content = f.read()
    
    # Create PDF
    doc = SimpleDocTemplate("demo_machine_learning.pdf", pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Split content into paragraphs
    paragraphs = content.split('\n\n')
    
    for para in paragraphs:
        if para.strip():
            # Check if it's a title or heading
            if para.startswith('Introduction') or para.startswith('Key Concepts') or para.startswith('Conclusion'):
                p = Paragraph(para, styles['Title'])
            elif para.startswith(('1.', '2.', '3.', '4.', '5.')):
                p = Paragraph(para, styles['Heading2'])
            else:
                p = Paragraph(para, styles['Normal'])
            
            story.append(p)
            story.append(Spacer(1, 12))
    
    doc.build(story)
    print("Demo PDF created: demo_machine_learning.pdf")

if __name__ == "__main__":
    create_demo_pdf()
