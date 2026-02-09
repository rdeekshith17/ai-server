"""
SecureGuard AI - PowerPoint Presentation Generator
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import nsmap
from pptx.oxml import parse_xml

# Create presentation with widescreen dimensions
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Colors
DARK_BG = RGBColor(15, 23, 42)  # #0f172a
BLUE = RGBColor(59, 130, 246)  # #3b82f6
CYAN = RGBColor(6, 182, 212)  # #06b6d4
WHITE = RGBColor(226, 232, 240)  # #e2e8f0
GRAY = RGBColor(148, 163, 184)  # #94a3b8
GREEN = RGBColor(34, 197, 94)  # #22c55e
RED = RGBColor(239, 68, 68)  # #ef4444
AMBER = RGBColor(245, 158, 11)  # #f59e0b
PURPLE = RGBColor(139, 92, 246)  # #8b5cf6

def add_background(slide, color=DARK_BG):
    """Add solid background color to slide"""
    background = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
    )
    background.fill.solid()
    background.fill.fore_color.rgb = color
    background.line.fill.background()
    # Send to back
    spTree = slide.shapes._spTree
    sp = background._element
    spTree.remove(sp)
    spTree.insert(2, sp)

def add_title(slide, text, top=Inches(0.5), font_size=44, color=BLUE):
    """Add title text to slide"""
    title_box = slide.shapes.add_textbox(Inches(0.5), top, Inches(12), Inches(1))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = True
    p.font.color.rgb = color
    return title_box

def add_subtitle(slide, text, top=Inches(1.2), font_size=28, color=GRAY):
    """Add subtitle text"""
    sub_box = slide.shapes.add_textbox(Inches(0.5), top, Inches(12), Inches(0.7))
    tf = sub_box.text_frame
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    return sub_box

def add_text_box(slide, text, left, top, width, height, font_size=18, color=WHITE, bold=False, align=PP_ALIGN.LEFT):
    """Add a text box"""
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.alignment = align
    return box

def add_bullet_points(slide, items, left, top, width, height, font_size=18, color=WHITE):
    """Add bullet point list"""
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    
    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = "• " + item
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.space_after = Pt(8)
    return box

def add_card(slide, title, content, left, top, width, height, title_color=CYAN, border_color=None):
    """Add a card-style box"""
    # Background
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = RGBColor(30, 41, 59)  # Slightly lighter
    if border_color:
        card.line.color.rgb = border_color
        card.line.width = Pt(2)
    else:
        card.line.fill.background()
    
    # Title
    if title:
        add_text_box(slide, title, left + Inches(0.15), top + Inches(0.1), 
                    width - Inches(0.3), Inches(0.4), font_size=16, color=title_color, bold=True)
    
    # Content
    if content:
        content_top = top + Inches(0.5) if title else top + Inches(0.15)
        add_text_box(slide, content, left + Inches(0.15), content_top,
                    width - Inches(0.3), height - Inches(0.6), font_size=14, color=GRAY)
    
    return card

def add_stat_card(slide, number, label, left, top, width=Inches(2.5), height=Inches(1.5)):
    """Add a statistics card"""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = RGBColor(30, 41, 59)
    card.line.fill.background()
    
    # Number
    add_text_box(slide, number, left, top + Inches(0.2), width, Inches(0.6), 
                font_size=36, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
    
    # Label
    add_text_box(slide, label, left, top + Inches(0.8), width, Inches(0.5),
                font_size=12, color=GRAY, align=PP_ALIGN.CENTER)

# ============================================
# SLIDE 1: Title Slide
# ============================================
slide1 = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
add_background(slide1)

# Logo/Icon placeholder
icon_box = add_text_box(slide1, "🛡️", Inches(6), Inches(1.5), Inches(1.5), Inches(1),
                        font_size=72, color=BLUE, align=PP_ALIGN.CENTER)

# Main title
add_text_box(slide1, "SECUREGUARD AI", Inches(0.5), Inches(2.5), Inches(12.5), Inches(1),
            font_size=60, color=BLUE, bold=True, align=PP_ALIGN.CENTER)

# Subtitle
add_text_box(slide1, "Next-Generation Shoplifting Detection Platform", 
            Inches(0.5), Inches(3.5), Inches(12.5), Inches(0.6),
            font_size=28, color=GRAY, align=PP_ALIGN.CENTER)

add_text_box(slide1, "Powered by Multi-Layer Artificial Intelligence",
            Inches(0.5), Inches(4.1), Inches(12.5), Inches(0.5),
            font_size=20, color=GRAY, align=PP_ALIGN.CENTER)

# Stats row
stats = [("94.7%", "Accuracy"), ("< 1 sec", "Detection"), ("2000%+", "ROI"), ("24/7", "Protection")]
for i, (num, label) in enumerate(stats):
    add_stat_card(slide1, num, label, Inches(1.5 + i * 2.8), Inches(5.3))

# ============================================
# SLIDE 2: The Problem
# ============================================
slide2 = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide2)
add_title(slide2, "The Problem")
add_subtitle(slide2, "Retail Theft: A Growing Crisis")

# Statistics
stats2 = [
    ("$112B", "Lost Annually"),
    ("37%", "Due to Shoplifting"),
    ("$461", "Per Incident"),
    ("2%", "Caught Traditionally")
]
for i, (num, label) in enumerate(stats2):
    add_stat_card(slide2, num, label, Inches(0.5 + i * 3.2), Inches(2.2), width=Inches(2.8))

# Problems list
problems = [
    "Manual CCTV monitoring is expensive and ineffective",
    "Security guards can't watch all cameras simultaneously", 
    "Incidents are discovered only after the fact",
    "Evidence collection is time-consuming",
    "High false alarm rates waste staff time"
]
add_text_box(slide2, "Current Solutions Fall Short:", Inches(0.5), Inches(4.2), 
            Inches(12), Inches(0.4), font_size=22, color=AMBER, bold=True)
add_bullet_points(slide2, problems, Inches(0.5), Inches(4.7), Inches(12), Inches(2.5))

# ============================================
# SLIDE 3: Our Solution
# ============================================
slide3 = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide3)
add_title(slide3, "Our Solution")
add_subtitle(slide3, "SecureGuard AI: Intelligent Protection")

# Flow diagram text
flow_text = """📹 Your Existing CCTV Cameras
                    ↓
    🤖 SecureGuard AI Engine
    [YOLO] [Pose] [Face] [GPT]
                    ↓
    🚨 Instant Alert + 📊 Evidence"""

add_text_box(slide3, flow_text, Inches(3.5), Inches(2.2), Inches(6), Inches(2.5),
            font_size=20, color=WHITE, align=PP_ALIGN.CENTER)

# Benefits
benefits = [
    ("✅ Works With Existing Cameras", "No new hardware needed"),
    ("⚡ Real-Time Detection", "Alerts within seconds"),
    ("🔒 Privacy-First", "Video stays on-premise")
]
for i, (title, desc) in enumerate(benefits):
    add_card(slide3, title, desc, Inches(0.5 + i * 4.2), Inches(5.2), Inches(3.8), Inches(1.3))

# ============================================
# SLIDE 4: 4-Layer AI Pipeline
# ============================================
slide4 = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide4)
add_title(slide4, "How It Works")
add_subtitle(slide4, "4-Layer AI Detection Pipeline")

layers = [
    ("Layer 1: YOLO", "Object Detection", "• People tracking\n• Bag detection\n• Hand positions\n• Products", BLUE),
    ("Layer 2: Pose", "Movement Analysis", "• Concealment\n• Pocket stuffing\n• Nervous behavior\n• Lookout patterns", PURPLE),
    ("Layer 3: DeepFace", "Face Recognition", "• Watchlist matching\n• Known offenders\n• Repeat visitors\n• Demographics", CYAN),
    ("Layer 4: GPT Vision", "Behavioral AI", "• Context analysis\n• Intent detection\n• Risk scoring\n• Recommendations", AMBER)
]

for i, (title, subtitle, content, color) in enumerate(layers):
    left = Inches(0.3 + i * 3.25)
    # Card background
    card = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(2.2), Inches(3), Inches(4))
    card.fill.solid()
    card.fill.fore_color.rgb = RgbColor(30, 41, 59)
    card.line.color.rgb = color
    card.line.width = Pt(3)
    
    add_text_box(slide4, title, left + Inches(0.1), Inches(2.35), Inches(2.8), Inches(0.4),
                font_size=16, color=color, bold=True)
    add_text_box(slide4, subtitle, left + Inches(0.1), Inches(2.75), Inches(2.8), Inches(0.3),
                font_size=14, color=GRAY)
    add_text_box(slide4, content, left + Inches(0.1), Inches(3.2), Inches(2.8), Inches(2.8),
                font_size=13, color=WHITE)

# Accuracy footer
add_text_box(slide4, "Combined Accuracy: 94.7%  |  False Positive Rate: <5%",
            Inches(0.5), Inches(6.5), Inches(12), Inches(0.4),
            font_size=20, color=GREEN, bold=True, align=PP_ALIGN.CENTER)

# ============================================
# SLIDE 5: Detection Example
# ============================================
slide5 = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide5)
add_title(slide5, "Detection in Action")
add_subtitle(slide5, "Real-Time Analysis Example")

# Live feed simulation
feed_box = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), Inches(2.2), Inches(5.5), Inches(4.5))
feed_box.fill.solid()
feed_box.fill.fore_color.rgb = RgbColor(15, 23, 42)
feed_box.line.color.rgb = BLUE
feed_box.line.width = Pt(2)

add_text_box(slide5, "📹 Live Camera Feed", Inches(0.7), Inches(2.4), Inches(5), Inches(0.4),
            font_size=16, color=CYAN, bold=True)

detection_log = """▶ Person #1 detected
▶ Bag detected near person
▶ Concealment motion detected!
▶ Hand-to-bag movement: HIGH RISK
▶ Generating alert..."""
add_text_box(slide5, detection_log, Inches(0.7), Inches(3), Inches(5), Inches(3.5),
            font_size=14, color=GREEN)

# AI Report
report_box = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.5), Inches(2.2), Inches(6.3), Inches(4.5))
report_box.fill.solid()
report_box.fill.fore_color.rgb = RgbColor(30, 41, 59)
report_box.line.color.rgb = RED
report_box.line.width = Pt(2)

add_text_box(slide5, "🚨 AI Analysis Report", Inches(6.7), Inches(2.4), Inches(5.8), Inches(0.4),
            font_size=16, color=RED, bold=True)

report_content = """Timestamp: 14:32:45
Camera: Aisle 3 - Electronics
Threat Level: CRITICAL (92%)

GPT Analysis:
"Male subject in dark hoodie observed 
picking up iPhone case, looking around 
multiple times, then placing item in 
jacket pocket. Concealment motion 
detected with high confidence."

Recommended: Immediate intervention"""
add_text_box(slide5, report_content, Inches(6.7), Inches(2.9), Inches(5.8), Inches(3.6),
            font_size=12, color=WHITE)

# ============================================
# SLIDE 6: Alerts
# ============================================
slide6 = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide6)
add_title(slide6, "Instant Alerts")
add_subtitle(slide6, "Multi-Channel Notification System")

alert_channels = [
    ("📱", "WhatsApp", "< 3 sec", "Photo + Location"),
    ("📧", "Email", "< 5 sec", "Full Report + Video"),
    ("🖥️", "Dashboard", "Real-time", "Live View"),
    ("📲", "Mobile App", "< 3 sec", "Push Notification")
]

for i, (icon, name, time, desc) in enumerate(alert_channels):
    left = Inches(0.5 + i * 3.2)
    card = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(2.3), Inches(2.8), Inches(2))
    card.fill.solid()
    card.fill.fore_color.rgb = RgbColor(30, 41, 59)
    card.line.fill.background()
    
    add_text_box(slide6, icon, left, Inches(2.4), Inches(2.8), Inches(0.6),
                font_size=36, color=WHITE, align=PP_ALIGN.CENTER)
    add_text_box(slide6, name, left, Inches(3), Inches(2.8), Inches(0.3),
                font_size=16, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    add_text_box(slide6, time, left, Inches(3.35), Inches(2.8), Inches(0.3),
                font_size=20, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
    add_text_box(slide6, desc, left, Inches(3.7), Inches(2.8), Inches(0.3),
                font_size=12, color=GRAY, align=PP_ALIGN.CENTER)

# Alert contents
add_text_box(slide6, "Every Alert Includes:", Inches(0.5), Inches(4.7), Inches(12), Inches(0.4),
            font_size=18, color=AMBER, bold=True)

alert_items = "📸 Snapshot  •  📍 Location  •  ⏰ Timestamp  •  📊 Confidence Score  •  📝 AI Summary  •  🎬 Video Clip"
add_text_box(slide6, alert_items, Inches(0.5), Inches(5.2), Inches(12), Inches(0.4),
            font_size=16, color=WHITE, align=PP_ALIGN.CENTER)

# ============================================
# SLIDE 7: Architecture
# ============================================
slide7 = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide7)
add_title(slide7, "Deployment Architecture")
add_subtitle(slide7, "Edge + Cloud for Maximum Privacy & Speed")

# Cloud box
cloud = slide7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(3), Inches(2), Inches(7), Inches(1.5))
cloud.fill.solid()
cloud.fill.fore_color.rgb = RgbColor(30, 41, 59)
cloud.line.color.rgb = CYAN
cloud.line.width = Pt(2)

add_text_box(slide7, "☁️ CENTRAL CLOUD SERVER", Inches(3.2), Inches(2.1), Inches(6.6), Inches(0.4),
            font_size=16, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
add_text_box(slide7, "Dashboard • Reports • User Management • Multi-Location", 
            Inches(3.2), Inches(2.5), Inches(6.6), Inches(0.4),
            font_size=12, color=GRAY, align=PP_ALIGN.CENTER)

# Arrow
add_text_box(slide7, "▲ Incidents Only (No raw video!)", Inches(5), Inches(3.6), Inches(3), Inches(0.4),
            font_size=12, color=GREEN, align=PP_ALIGN.CENTER)

# Store boxes
stores = ["🏪 STORE 1", "🏪 STORE 2", "🏪 STORE 3"]
for i, store in enumerate(stores):
    left = Inches(1 + i * 4)
    box = slide7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(4.3), Inches(3.5), Inches(2.2))
    box.fill.solid()
    box.fill.fore_color.rgb = RgbColor(30, 41, 59)
    box.line.color.rgb = BLUE
    box.line.width = Pt(2)
    
    add_text_box(slide7, store, left + Inches(0.1), Inches(4.4), Inches(3.3), Inches(0.4),
                font_size=14, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    add_text_box(slide7, "Edge Device\n• AI Models\n• Local Processing\n📹📹📹📹",
                left + Inches(0.1), Inches(4.85), Inches(3.3), Inches(1.5),
                font_size=11, color=GRAY, align=PP_ALIGN.CENTER)

# Benefits row
benefits7 = ["✅ Video stays on-premise", "✅ Instant local processing", "✅ Low bandwidth", "✅ Easy to scale"]
for i, benefit in enumerate(benefits7):
    add_text_box(slide7, benefit, Inches(0.5 + i * 3.2), Inches(6.7), Inches(3), Inches(0.4),
                font_size=14, color=GREEN)

# ============================================
# SLIDE 8: ROI
# ============================================
slide8 = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide8)
add_title(slide8, "Return on Investment")
add_subtitle(slide8, "SecureGuard Pays for Itself")

# Table
table_data = [
    ("Metric", "Before", "After"),
    ("Monthly theft incidents", "50", "8"),
    ("Average loss per incident", "$150", "$150"),
    ("Monthly loss", "$7,500", "$1,200"),
    ("Monthly savings", "-", "$6,300")
]

table_top = Inches(2.3)
for row_idx, row in enumerate(table_data):
    for col_idx, cell in enumerate(row):
        left = Inches(0.5 + col_idx * 2)
        top = table_top + Inches(row_idx * 0.5)
        
        if row_idx == 0:
            color = CYAN
            bold = True
        elif col_idx == 2 and row_idx > 0:
            color = GREEN
            bold = row_idx == 4
        else:
            color = WHITE
            bold = row_idx == 4
            
        add_text_box(slide8, cell, left, top, Inches(1.8), Inches(0.4),
                    font_size=16, color=color, bold=bold)

# ROI Summary box
roi_box = slide8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7), Inches(2.3), Inches(5.8), Inches(4))
roi_box.fill.solid()
roi_box.fill.fore_color.rgb = RgbColor(20, 40, 30)
roi_box.line.color.rgb = GREEN
roi_box.line.width = Pt(2)

add_text_box(slide8, "ROI Summary", Inches(7.2), Inches(2.5), Inches(5.4), Inches(0.4),
            font_size=20, color=GREEN, bold=True, align=PP_ALIGN.CENTER)
add_text_box(slide8, "Monthly Subscription: $299", Inches(7.2), Inches(3.1), Inches(5.4), Inches(0.3),
            font_size=16, color=WHITE, align=PP_ALIGN.CENTER)
add_text_box(slide8, "Monthly Savings: $6,300", Inches(7.2), Inches(3.5), Inches(5.4), Inches(0.3),
            font_size=16, color=GREEN, align=PP_ALIGN.CENTER)
add_text_box(slide8, "Net Monthly Benefit:", Inches(7.2), Inches(4.2), Inches(5.4), Inches(0.3),
            font_size=14, color=GRAY, align=PP_ALIGN.CENTER)
add_text_box(slide8, "$6,001", Inches(7.2), Inches(4.5), Inches(5.4), Inches(0.5),
            font_size=36, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
add_text_box(slide8, "Annual ROI: 2,107%", Inches(7.2), Inches(5.2), Inches(5.4), Inches(0.4),
            font_size=20, color=AMBER, bold=True, align=PP_ALIGN.CENTER)
add_text_box(slide8, "Payback Period: < 2 weeks", Inches(7.2), Inches(5.7), Inches(5.4), Inches(0.3),
            font_size=14, color=GRAY, align=PP_ALIGN.CENTER)

# ============================================
# SLIDE 9: Pricing
# ============================================
slide9 = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide9)
add_title(slide9, "Pricing Plans")
add_subtitle(slide9, "Flexible Plans for Every Business")

plans = [
    ("Starter", "$99", "/month", "Up to 4 cameras", 
     ["✅ All 4 AI layers", "✅ Real-time alerts", "✅ Web dashboard", "✅ Email support", "❌ Face recognition", "❌ API access"],
     False),
    ("Professional", "$299", "/month", "Up to 16 cameras",
     ["✅ All Starter features", "✅ Face recognition", "✅ Watchlist matching", "✅ GPT analysis", "✅ Advanced analytics", "✅ Priority support"],
     True),
    ("Enterprise", "Custom", "", "Unlimited cameras",
     ["✅ All Pro features", "✅ Multi-location", "✅ Custom integrations", "✅ Dedicated manager", "✅ On-site training", "✅ SLA guarantee"],
     False)
]

for i, (name, price, period, cameras, features, featured) in enumerate(plans):
    left = Inches(0.5 + i * 4.2)
    
    card = slide9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(2.2), Inches(3.8), Inches(4.8))
    card.fill.solid()
    card.fill.fore_color.rgb = RgbColor(30, 41, 59)
    card.line.color.rgb = AMBER if featured else BLUE
    card.line.width = Pt(3 if featured else 1)
    
    if featured:
        add_text_box(slide9, "MOST POPULAR", left + Inches(0.9), Inches(2.35), Inches(2), Inches(0.3),
                    font_size=10, color=AMBER, bold=True, align=PP_ALIGN.CENTER)
    
    add_text_box(slide9, name, left, Inches(2.7), Inches(3.8), Inches(0.4),
                font_size=22, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    add_text_box(slide9, price, left, Inches(3.1), Inches(3.8), Inches(0.5),
                font_size=36, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
    add_text_box(slide9, period, left, Inches(3.55), Inches(3.8), Inches(0.3),
                font_size=12, color=GRAY, align=PP_ALIGN.CENTER)
    add_text_box(slide9, cameras, left, Inches(3.85), Inches(3.8), Inches(0.3),
                font_size=12, color=GRAY, align=PP_ALIGN.CENTER)
    
    features_text = "\n".join(features)
    add_text_box(slide9, features_text, left + Inches(0.2), Inches(4.3), Inches(3.4), Inches(2.5),
                font_size=11, color=WHITE)

# ============================================
# SLIDE 10: CTA
# ============================================
slide10 = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide10)

add_text_box(slide10, "Get Started Today", Inches(0.5), Inches(1.5), Inches(12.5), Inches(0.8),
            font_size=48, color=BLUE, bold=True, align=PP_ALIGN.CENTER)
add_text_box(slide10, "14-Day Free Trial", Inches(0.5), Inches(2.4), Inches(12.5), Inches(0.5),
            font_size=28, color=GRAY, align=PP_ALIGN.CENTER)

# Trial box
trial_box = slide10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4), Inches(3.2), Inches(5.5), Inches(2.3))
trial_box.fill.solid()
trial_box.fill.fore_color.rgb = RgbColor(20, 40, 30)
trial_box.line.color.rgb = GREEN
trial_box.line.width = Pt(2)

add_text_box(slide10, "🎁 Free Pilot Program", Inches(4.2), Inches(3.4), Inches(5.1), Inches(0.4),
            font_size=18, color=GREEN, bold=True, align=PP_ALIGN.CENTER)

trial_features = "• Full system access\n• Up to 4 cameras\n• All AI features enabled\n• No credit card required\n• No obligation"
add_text_box(slide10, trial_features, Inches(4.4), Inches(3.9), Inches(4.7), Inches(1.5),
            font_size=14, color=WHITE)

# Contact info
add_text_box(slide10, "📧 sales@secureguard.ai    📱 +91 XXXXX XXXXX    🌐 www.secureguard.ai",
            Inches(0.5), Inches(6), Inches(12.5), Inches(0.4),
            font_size=18, color=GRAY, align=PP_ALIGN.CENTER)

# ============================================
# SLIDE 11: Thank You
# ============================================
slide11 = prs.slides.add_slide(prs.slide_layouts[6])
add_background(slide11)

add_text_box(slide11, "🛡️", Inches(0.5), Inches(2), Inches(12.5), Inches(1),
            font_size=72, color=BLUE, align=PP_ALIGN.CENTER)
add_text_box(slide11, "Thank You!", Inches(0.5), Inches(3), Inches(12.5), Inches(0.8),
            font_size=54, color=BLUE, bold=True, align=PP_ALIGN.CENTER)
add_text_box(slide11, "Questions?", Inches(0.5), Inches(3.9), Inches(12.5), Inches(0.5),
            font_size=28, color=GRAY, align=PP_ALIGN.CENTER)

add_text_box(slide11, "SECUREGUARD AI", Inches(0.5), Inches(5), Inches(12.5), Inches(0.5),
            font_size=24, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
add_text_box(slide11, "Protecting Your Business, 24/7", Inches(0.5), Inches(5.5), Inches(12.5), Inches(0.4),
            font_size=18, color=GRAY, align=PP_ALIGN.CENTER)

add_text_box(slide11, "📧 sales@secureguard.ai  •  📱 +91 XXXXX XXXXX  •  🌐 www.secureguard.ai",
            Inches(0.5), Inches(6.3), Inches(12.5), Inches(0.4),
            font_size=16, color=GRAY, align=PP_ALIGN.CENTER)

# Save presentation
output_path = "/app/docs/SecureGuard_Presentation.pptx"
prs.save(output_path)
print(f"✅ Presentation saved to: {output_path}")
