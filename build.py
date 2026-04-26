#!/usr/bin/env python3
"""
AI上司プロジェクト - メンバー共有サイトビルドスクリプト
ブログ記事とメルマガをHTMLサイトに変換する
"""
import os
import re
import glob
import html
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BLOG_DIR = BASE_DIR / "note_articles" / "output"
MAIL_DIR = BASE_DIR / "newsletter" / "output"
SITE_DIR = BASE_DIR / "site"
IMAGE_DIR = BASE_DIR / "image"

# Simple markdown to HTML converter
def md_to_html(text):
    lines = text.split('\n')
    result = []
    in_list = False
    in_blockquote = False

    for line in lines:
        stripped = line.strip()

        # Empty line
        if not stripped:
            if in_list:
                result.append('</ul>')
                in_list = False
            if in_blockquote:
                result.append('</blockquote>')
                in_blockquote = False
            result.append('')
            continue

        # Headings
        if stripped.startswith('## '):
            if in_list:
                result.append('</ul>')
                in_list = False
            result.append(f'<h2>{format_inline(stripped[3:])}</h2>')
            continue
        if stripped.startswith('### '):
            if in_list:
                result.append('</ul>')
                in_list = False
            result.append(f'<h3>{format_inline(stripped[4:])}</h3>')
            continue

        # Blockquote
        if stripped.startswith('> '):
            if not in_blockquote:
                result.append('<blockquote>')
                in_blockquote = True
            result.append(f'<p>{format_inline(stripped[2:])}</p>')
            continue

        # List items
        if stripped.startswith('- '):
            if not in_list:
                result.append('<ul>')
                in_list = True
            result.append(f'<li>{format_inline(stripped[2:])}</li>')
            continue

        # Horizontal rule
        if stripped == '---':
            if in_list:
                result.append('</ul>')
                in_list = False
            result.append('<hr>')
            continue

        # Regular paragraph
        if in_list:
            result.append('</ul>')
            in_list = False
        result.append(f'<p>{format_inline(stripped)}</p>')

    if in_list:
        result.append('</ul>')
    if in_blockquote:
        result.append('</blockquote>')

    return '\n'.join(result)

def format_inline(text):
    text = html.escape(text)
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Emoji markers for dialog examples
    text = text.replace('&#x274C;', '<span class="ng">&#x274C;</span>')
    text = text.replace('&#x2B55;', '<span class="ok">&#x2B55;</span>')
    return text

def parse_frontmatter(content):
    """Parse YAML-like frontmatter from markdown file"""
    meta = {}
    body = content
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            fm = parts[1].strip()
            for line in fm.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    meta[key.strip()] = val.strip()
            body = parts[2]
    return meta, body

def extract_thumbnail(body):
    """Extract thumbnail instructions and article body"""
    thumb = {}
    article = body

    # Find thumbnail section
    thumb_match = re.search(r'#\s*サムネイル指示.*?\n(.*?)(?=\n---|\n#\s)', body, re.DOTALL)
    if thumb_match:
        thumb_text = thumb_match.group(1)
        for line in thumb_text.strip().split('\n'):
            line = line.strip()
            if line.startswith('- '):
                line = line[2:]
                if ':' in line:
                    k, v = line.split(':', 1)
                    thumb[k.strip()] = v.strip()

    # Extract article body after "以下を note にコピペ"
    copy_match = re.search(r'#\s*以下を\s*note\s*にコピペ\s*\n---\n(.*)', body, re.DOTALL)
    if copy_match:
        article = copy_match.group(1).strip()

    return thumb, article

def generate_illustration_svg(thumb, article_id):
    """Generate a simple SVG illustration based on thumbnail instructions"""
    bg_color = thumb.get('背景色', '#EAF0F6')
    main_copy = thumb.get('メインコピー', '')
    sub_copy = thumb.get('サブコピー', '')

    # Extract hex color if present
    color_match = re.search(r'#[0-9A-Fa-f]{6}', bg_color)
    hex_color = color_match.group(0) if color_match else '#4A7AB5'

    # Generate complementary colors
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    light_bg = f'rgb({min(r+60,255)},{min(g+60,255)},{min(b+60,255)})'
    dark_text = f'rgb({max(r-80,0)},{max(g-80,0)},{max(b-80,0)})'

    svg = f'''<svg viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg" class="article-illustration">
  <defs>
    <linearGradient id="bg{article_id}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{hex_color};stop-opacity:0.15"/>
      <stop offset="100%" style="stop-color:{hex_color};stop-opacity:0.05"/>
    </linearGradient>
  </defs>
  <rect width="800" height="400" rx="16" fill="url(#bg{article_id})"/>
  <circle cx="650" cy="200" r="120" fill="{hex_color}" opacity="0.08"/>
  <circle cx="680" cy="160" r="80" fill="{hex_color}" opacity="0.06"/>
  <rect x="60" y="140" width="6" height="120" rx="3" fill="{hex_color}" opacity="0.6"/>
  <text x="90" y="195" font-family="'Noto Sans JP', sans-serif" font-size="32" font-weight="700" fill="{dark_text}">{html.escape(main_copy)}</text>
  <text x="90" y="240" font-family="'Noto Sans JP', sans-serif" font-size="18" fill="{dark_text}" opacity="0.6">{html.escape(sub_copy)}</text>
</svg>'''
    return svg

def build_blog_page(articles):
    """Build the blog articles page"""
    cards = []
    for a in articles:
        tid = a['meta'].get('topic_id', '?')
        title = a['meta'].get('title', 'Untitled')
        category = a['meta'].get('category', '')
        phase = a['meta'].get('phase', '1')
        phase_label = {'1': '認知期', '2': '信頼期', '3': '行動転換期'}.get(phase, '')

        cards.append(f'''
        <div class="card" data-category="{category}" data-phase="{phase}" onclick="showArticle({tid})">
            <div class="card-phase phase-{phase}">{phase_label}</div>
            <div class="card-category">{category}</div>
            <h3 class="card-title">{html.escape(title)}</h3>
            <div class="card-id">#{tid}</div>
        </div>''')

    # Full article modals
    modals = []
    for a in articles:
        tid = a['meta'].get('topic_id', '?')
        title = a['meta'].get('title', '')
        tags = a['meta'].get('tags', '')
        svg = a.get('svg', '')
        body_html = a.get('body_html', '')

        modals.append(f'''
        <div class="article-modal" id="article-{tid}">
            <div class="modal-content">
                <button class="modal-close" onclick="closeArticle()">&times;</button>
                <div class="article-header">
                    <h1>{html.escape(title)}</h1>
                    <div class="article-tags">{html.escape(tags)}</div>
                </div>
                <div class="article-illustration-wrap">{svg}</div>
                <div class="article-body">{body_html}</div>
            </div>
        </div>''')

    return '\n'.join(cards), '\n'.join(modals)

def build_mail_page(mails):
    """Build the newsletter page"""
    cards = []
    for m in mails:
        mid = m['meta'].get('mail_id', '?')
        subject = m['meta'].get('subject', 'Untitled')
        phase = m['meta'].get('phase', '1')
        phase_name = m['meta'].get('phase_name', '')

        cards.append(f'''
        <div class="mail-card" data-phase="{phase}" onclick="showMail({mid})">
            <div class="mail-number">#{mid}</div>
            <div class="mail-phase phase-{phase}">{phase_name}</div>
            <h3 class="mail-subject">{html.escape(subject)}</h3>
        </div>''')

    modals = []
    for m in mails:
        mid = m['meta'].get('mail_id', '?')
        subject = m['meta'].get('subject', '')
        phase_name = m['meta'].get('phase_name', '')
        body_html = m.get('body_html', '')

        modals.append(f'''
        <div class="article-modal" id="mail-{mid}">
            <div class="modal-content mail-modal-content">
                <button class="modal-close" onclick="closeMail()">&times;</button>
                <div class="mail-header">
                    <div class="mail-meta-badge">{phase_name} | #{mid}/50</div>
                    <h1>{html.escape(subject)}</h1>
                </div>
                <div class="mail-body">{body_html}</div>
            </div>
        </div>''')

    return '\n'.join(cards), '\n'.join(modals)

def main():
    # Load blog articles
    articles = []
    for fp in sorted(glob.glob(str(BLOG_DIR / "article_*.md"))):
        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()
        meta, body = parse_frontmatter(content)
        thumb, article_text = extract_thumbnail(body)
        tid = meta.get('topic_id', '0')
        svg = generate_illustration_svg(thumb, tid)
        body_html = md_to_html(article_text)
        articles.append({
            'meta': meta,
            'thumb': thumb,
            'svg': svg,
            'body_html': body_html,
        })
    articles.sort(key=lambda x: int(x['meta'].get('topic_id', 0)))

    # Load newsletters
    mails = []
    for fp in sorted(glob.glob(str(MAIL_DIR / "mail_*.md"))):
        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()
        meta, body = parse_frontmatter(content)
        body_html = md_to_html(body.strip())
        mails.append({
            'meta': meta,
            'body_html': body_html,
        })
    mails.sort(key=lambda x: int(x['meta'].get('mail_id', 0)))

    blog_cards, blog_modals = build_blog_page(articles)
    mail_cards, mail_modals = build_mail_page(mails)

    # Copy avatar image
    avatar_src = list(IMAGE_DIR.glob("*.png"))
    avatar_filename = avatar_src[0].name if avatar_src else ""

    # Generate HTML
    html_content = generate_html(blog_cards, blog_modals, mail_cards, mail_modals,
                                  len(articles), len(mails), avatar_filename)

    out_path = SITE_DIR / "index.html"
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # Copy avatar to site dir
    if avatar_src:
        import shutil
        shutil.copy2(avatar_src[0], SITE_DIR / avatar_filename)

    print(f"Built: {len(articles)} articles, {len(mails)} newsletters")
    print(f"Output: {out_path}")

def generate_html(blog_cards, blog_modals, mail_cards, mail_modals,
                   num_articles, num_mails, avatar_filename):
    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI上司 - コンテンツプレビュー</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700&display=swap');

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

:root {{
    --primary: #1A2E4A;
    --primary-light: #2D4A6F;
    --accent: #E8913A;
    --bg: #F7F8FA;
    --card-bg: #FFFFFF;
    --text: #2D3748;
    --text-light: #718096;
    --border: #E2E8F0;
    --phase-1: #4299E1;
    --phase-2: #48BB78;
    --phase-3: #ED8936;
    --phase-4: #9F7AEA;
    --phase-5: #F56565;
}}

body {{
    font-family: 'Noto Sans JP', sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.8;
}}

/* Header */
.header {{
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
    color: white;
    padding: 2rem 0;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}}

.header-inner {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 2rem;
    display: flex;
    align-items: center;
    gap: 1.5rem;
}}

.avatar {{
    width: 56px;
    height: 56px;
    border-radius: 50%;
    border: 3px solid rgba(255,255,255,0.3);
    object-fit: cover;
}}

.header-text h1 {{
    font-size: 1.3rem;
    font-weight: 700;
    letter-spacing: 0.05em;
}}

.header-text p {{
    font-size: 0.8rem;
    opacity: 0.7;
    margin-top: 2px;
}}

/* Navigation */
.nav {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 1.5rem 2rem 0;
    display: flex;
    gap: 0.5rem;
}}

.nav-btn {{
    padding: 0.7rem 1.5rem;
    border: none;
    background: var(--card-bg);
    color: var(--text-light);
    font-family: inherit;
    font-size: 0.95rem;
    font-weight: 500;
    border-radius: 8px 8px 0 0;
    cursor: pointer;
    transition: all 0.2s;
    border-bottom: 3px solid transparent;
}}

.nav-btn.active {{
    color: var(--primary);
    border-bottom-color: var(--accent);
    box-shadow: 0 -2px 8px rgba(0,0,0,0.05);
}}

.nav-btn:hover {{
    color: var(--primary);
}}

.nav-count {{
    font-size: 0.75rem;
    background: var(--border);
    padding: 2px 8px;
    border-radius: 10px;
    margin-left: 6px;
}}

/* Content Area */
.content {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 2rem 3rem;
}}

.tab-content {{
    display: none;
    background: var(--card-bg);
    border-radius: 0 8px 8px 8px;
    padding: 2rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}}

.tab-content.active {{
    display: block;
}}

/* Filters */
.filters {{
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border);
}}

.filter-btn {{
    padding: 0.4rem 1rem;
    border: 1px solid var(--border);
    background: white;
    border-radius: 20px;
    font-family: inherit;
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.2s;
}}

.filter-btn.active {{
    background: var(--primary);
    color: white;
    border-color: var(--primary);
}}

/* Blog Cards Grid */
.cards-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
}}

.card {{
    background: white;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.2rem;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
}}

.card:hover {{
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    transform: translateY(-2px);
}}

.card-phase {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 500;
    color: white;
    margin-bottom: 0.5rem;
}}

.phase-1 {{ background: var(--phase-1); }}
.phase-2 {{ background: var(--phase-2); }}
.phase-3 {{ background: var(--phase-3); }}
.phase-4 {{ background: var(--phase-4); }}
.phase-5 {{ background: var(--phase-5); }}

.card-category {{
    font-size: 0.75rem;
    color: var(--text-light);
    margin-bottom: 0.3rem;
}}

.card-title {{
    font-size: 0.95rem;
    font-weight: 500;
    line-height: 1.5;
}}

.card-id {{
    position: absolute;
    top: 1rem;
    right: 1rem;
    font-size: 0.75rem;
    color: var(--text-light);
}}

/* Mail Cards */
.mail-cards {{
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}}

.mail-card {{
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem 1.2rem;
    background: white;
    border: 1px solid var(--border);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
}}

.mail-card:hover {{
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border-color: var(--primary-light);
}}

.mail-number {{
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--text-light);
    min-width: 36px;
}}

.mail-phase {{
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.65rem;
    font-weight: 500;
    color: white;
    white-space: nowrap;
}}

.mail-subject {{
    font-size: 0.9rem;
    font-weight: 500;
    flex: 1;
}}

/* Modal */
.article-modal {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 200;
    overflow-y: auto;
    padding: 2rem;
}}

.article-modal.show {{
    display: flex;
    justify-content: center;
    align-items: flex-start;
}}

.modal-content {{
    background: white;
    border-radius: 12px;
    max-width: 780px;
    width: 100%;
    padding: 2.5rem;
    position: relative;
    margin: 2rem auto;
    box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}}

.mail-modal-content {{
    max-width: 640px;
}}

.modal-close {{
    position: sticky;
    top: 0;
    float: right;
    width: 40px;
    height: 40px;
    border: none;
    background: var(--bg);
    border-radius: 50%;
    font-size: 1.5rem;
    cursor: pointer;
    color: var(--text-light);
    z-index: 10;
}}

.modal-close:hover {{
    background: var(--border);
}}

.article-header h1 {{
    font-size: 1.5rem;
    font-weight: 700;
    line-height: 1.4;
    margin-bottom: 0.5rem;
    color: var(--primary);
}}

.article-tags {{
    font-size: 0.8rem;
    color: var(--text-light);
    margin-bottom: 1.5rem;
}}

.article-illustration-wrap {{
    margin: 1.5rem 0;
    border-radius: 12px;
    overflow: hidden;
}}

.article-illustration {{
    width: 100%;
    height: auto;
}}

.article-body, .mail-body {{
    font-size: 0.95rem;
    line-height: 2;
    color: var(--text);
}}

.article-body h2 {{
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--primary);
    margin: 2rem 0 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--accent);
}}

.article-body h3 {{
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--primary-light);
    margin: 1.5rem 0 0.8rem;
}}

.article-body p {{
    margin-bottom: 1rem;
}}

.article-body blockquote {{
    border-left: 4px solid var(--accent);
    padding: 0.8rem 1.2rem;
    margin: 1rem 0;
    background: #FFF8F0;
    border-radius: 0 8px 8px 0;
}}

.article-body ul {{
    padding-left: 1.5rem;
    margin-bottom: 1rem;
}}

.article-body li {{
    margin-bottom: 0.5rem;
}}

.article-body hr {{
    border: none;
    border-top: 1px solid var(--border);
    margin: 2rem 0;
}}

.article-body .ng {{
    color: #E53E3E;
    font-weight: 700;
}}

.article-body .ok {{
    color: #38A169;
    font-weight: 700;
}}

/* Mail specific */
.mail-header {{
    margin-bottom: 1.5rem;
}}

.mail-header h1 {{
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--primary);
    line-height: 1.4;
}}

.mail-meta-badge {{
    display: inline-block;
    font-size: 0.75rem;
    color: var(--text-light);
    margin-bottom: 0.5rem;
    padding: 2px 10px;
    background: var(--bg);
    border-radius: 12px;
}}

.mail-body h2 {{
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--primary);
    margin: 1.5rem 0 0.8rem;
}}

.mail-body p {{
    margin-bottom: 0.8rem;
}}

.mail-body hr {{
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.5rem 0;
}}

/* Stats bar */
.stats {{
    display: flex;
    gap: 2rem;
    padding: 1rem 0;
    margin-bottom: 1rem;
    border-bottom: 1px solid var(--border);
}}

.stat {{
    text-align: center;
}}

.stat-num {{
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--primary);
}}

.stat-label {{
    font-size: 0.75rem;
    color: var(--text-light);
}}

@media (max-width: 768px) {{
    .header-inner {{ padding: 0 1rem; }}
    .nav {{ padding: 1rem 1rem 0; }}
    .content {{ padding: 0 1rem 2rem; }}
    .modal-content {{ padding: 1.5rem; margin: 1rem; }}
    .cards-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>

<header class="header">
    <div class="header-inner">
        <img src="{avatar_filename}" alt="AI上司" class="avatar">
        <div class="header-text">
            <h1>AI上司 コンテンツプレビュー</h1>
            <p>メンバー共有用 - note記事 & メルマガ一覧</p>
        </div>
    </div>
</header>

<nav class="nav">
    <button class="nav-btn active" onclick="switchTab('blog')">
        note記事<span class="nav-count">{num_articles}</span>
    </button>
    <button class="nav-btn" onclick="switchTab('mail')">
        メルマガ<span class="nav-count">{num_mails}</span>
    </button>
</nav>

<main class="content">
    <!-- Blog Tab -->
    <div class="tab-content active" id="tab-blog">
        <div class="stats">
            <div class="stat"><div class="stat-num">{num_articles}</div><div class="stat-label">記事数</div></div>
            <div class="stat"><div class="stat-num">6</div><div class="stat-label">カテゴリ</div></div>
            <div class="stat"><div class="stat-num">3</div><div class="stat-label">フェーズ</div></div>
        </div>
        <div class="filters" id="blog-filters">
            <button class="filter-btn active" onclick="filterBlog('all')">すべて</button>
            <button class="filter-btn" onclick="filterBlog('部下マネジメント')">部下マネジメント</button>
            <button class="filter-btn" onclick="filterBlog('上司対応')">上司対応</button>
            <button class="filter-btn" onclick="filterBlog('1on1')">1on1</button>
            <button class="filter-btn" onclick="filterBlog('評価')">評価</button>
            <button class="filter-btn" onclick="filterBlog('キャリア・メンタル')">キャリア・メンタル</button>
        </div>
        <div class="cards-grid" id="blog-grid">
            {blog_cards}
        </div>
    </div>

    <!-- Mail Tab -->
    <div class="tab-content" id="tab-mail">
        <div class="stats">
            <div class="stat"><div class="stat-num">{num_mails}</div><div class="stat-label">配信数</div></div>
            <div class="stat"><div class="stat-num">5</div><div class="stat-label">フェーズ</div></div>
        </div>
        <div class="filters" id="mail-filters">
            <button class="filter-btn active" onclick="filterMail('all')">すべて</button>
            <button class="filter-btn" onclick="filterMail('1')">Phase 1: 共感と安心</button>
            <button class="filter-btn" onclick="filterMail('2')">Phase 2: 常識の解体</button>
            <button class="filter-btn" onclick="filterMail('3')">Phase 3: 新しい視点</button>
            <button class="filter-btn" onclick="filterMail('4')">Phase 4: 実践と変化</button>
            <button class="filter-btn" onclick="filterMail('5')">Phase 5: 未来と決断</button>
        </div>
        <div class="mail-cards" id="mail-grid">
            {mail_cards}
        </div>
    </div>
</main>

<!-- Blog Modals -->
{blog_modals}

<!-- Mail Modals -->
{mail_modals}

<script>
function switchTab(tab) {{
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + tab).classList.add('active');
    event.target.classList.add('active');
}}

function filterBlog(category) {{
    document.querySelectorAll('#blog-filters .filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    document.querySelectorAll('#blog-grid .card').forEach(card => {{
        if (category === 'all' || card.dataset.category === category) {{
            card.style.display = '';
        }} else {{
            card.style.display = 'none';
        }}
    }});
}}

function filterMail(phase) {{
    document.querySelectorAll('#mail-filters .filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    document.querySelectorAll('#mail-grid .mail-card').forEach(card => {{
        if (phase === 'all' || card.dataset.phase === phase) {{
            card.style.display = '';
        }} else {{
            card.style.display = 'none';
        }}
    }});
}}

function showArticle(id) {{
    document.getElementById('article-' + id).classList.add('show');
    document.body.style.overflow = 'hidden';
}}

function closeArticle() {{
    document.querySelectorAll('.article-modal').forEach(m => m.classList.remove('show'));
    document.body.style.overflow = '';
}}

function showMail(id) {{
    document.getElementById('mail-' + id).classList.add('show');
    document.body.style.overflow = 'hidden';
}}

function closeMail() {{
    document.querySelectorAll('.article-modal').forEach(m => m.classList.remove('show'));
    document.body.style.overflow = '';
}}

// Close modal on backdrop click
document.addEventListener('click', function(e) {{
    if (e.target.classList.contains('article-modal')) {{
        e.target.classList.remove('show');
        document.body.style.overflow = '';
    }}
}});

// Close modal on Escape
document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') {{
        document.querySelectorAll('.article-modal').forEach(m => m.classList.remove('show'));
        document.body.style.overflow = '';
    }}
}});
</script>

</body>
</html>'''

if __name__ == '__main__':
    main()
