import re
import html
import hashlib
import logging
from datetime import datetime
import email.utils
from bs4 import BeautifulSoup
import feedparser
from flask import Flask, jsonify, render_template, request

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# RSS Feeds Configuration
FEEDS = [
    {
        'id': 'arxiv_ai',
        'name': 'arXiv Artificial Intelligence',
        'url': 'https://rss.arxiv.org/rss/cs.AI',
        'default_category': 'Artificial Intelligence',
        'source': 'arXiv'
    },
    {
        'id': 'arxiv_ml',
        'name': 'arXiv Machine Learning',
        'url': 'https://rss.arxiv.org/rss/cs.LG',
        'default_category': 'Machine Learning',
        'source': 'arXiv'
    },
    {
        'id': 'arxiv_cv',
        'name': 'arXiv Computer Vision',
        'url': 'https://rss.arxiv.org/rss/cs.CV',
        'default_category': 'Computer Vision',
        'source': 'arXiv'
    },
    {
        'id': 'arxiv_nlp',
        'name': 'arXiv Computation & Language (NLP)',
        'url': 'https://rss.arxiv.org/rss/cs.CL',
        'default_category': 'Natural Language Processing',
        'source': 'arXiv'
    },
    {
        'id': 'mit_ai',
        'name': 'MIT News - Artificial Intelligence',
        'url': 'https://news.mit.edu/rss/topic/artificial-intelligence2',
        'default_category': 'General AI',
        'source': 'MIT News'
    },
    {
        'id': 'bair_blog',
        'name': 'Berkeley AI Research Blog',
        'url': 'https://bair.berkeley.edu/blog/feed.xml',
        'default_category': 'AI Research',
        'source': 'Berkeley AI Research'
    }
]

# Global cache
FEED_CACHE = {
    'items': [],
    'last_updated': None
}

def clean_latex(text):
    """
    Cleans LaTeX characters and expressions often found in arXiv abstracts.
    """
    if not text:
        return ""
    # Replace math block symbols $$...$$ with just ...
    text = re.sub(r'\$\$(.*?)\$\$', r'\1', text)
    # Replace math inline symbols $...$ with ...
    text = re.sub(r'\$(.*?)\$', r'\1', text)
    # Remove LaTeX commands like \text{...}, \mathbf{...}, \emph{...}
    text = re.sub(r'\\(?:text|mathbf|mathcal|emph|mathrm|tilde|hat|bar|mathbf|boldsymbol)\{(.*?)\}', r'\1', text)
    # Remove other slash commands
    text = text.replace('\\le', '<=').replace('\\ge', '>=').replace('\\ne', '!=').replace('\\approx', '≈')
    text = text.replace('\\in', 'in').replace('\\times', 'x').replace('\\rightarrow', '→').replace('\\infty', '∞')
    text = text.replace('\\_','_').replace('\\%','%')
    # Clean up multi-backslashes or remaining backslashes
    text = re.sub(r'\\', '', text)
    return text

def clean_title(title):
    """
    Cleans title by removing brackets and arXiv prefixes.
    Example: "Title. (arXiv:2304.12345v1 [cs.AI])" -> "Title"
    """
    if not title:
        return ""
    # Remove arXiv ID suffixes commonly found in title feeds
    title = re.sub(r'\s*\(\s*arXiv:.*?\s*\)', '', title)
    title = re.sub(r'\s*\[\s*cs\..*?\s*\]', '', title)
    # Clean up tailing dots and whitespace
    title = title.strip().rstrip('.')
    return clean_latex(title)

def clean_summary(summary_html):
    """
    Extracts text from HTML, removes arXiv prefixes/suffixes, and cleans formatting.
    """
    if not summary_html:
        return ""
    # Parse HTML using BeautifulSoup
    soup = BeautifulSoup(summary_html, "html.parser")
    # arXiv summaries often contain links to PDF, etc. We just want the paragraph text.
    # Get all paragraph text
    text = soup.get_text(separator=' ')
    
    # Unescape HTML entities
    text = html.unescape(text)
    
    # Remove arXiv header information like "arXiv:2304.12345v1 [cs.AI] 18 Jun 2023" or similar
    # Sometimes it shows at the very beginning of the feed summary
    text = re.sub(r'^arXiv:\d{4}\.\d{4,5}(v\d+)?\s+\[[a-zA-Z\-\.]+\]\s+(?:[a-zA-Z\s,]+)?\d{4}\s*', '', text)
    text = re.sub(r'^arXiv:\S+\s*', '', text)
    
    # Clean up LaTeX formatting
    text = clean_latex(text)
    
    # Clean up spacing
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_date(date_str, date_parsed_tuple=None):
    """
    Parses a publication date into a datetime object.
    Falls back to parsed time tuple from feedparser if available.
    """
    if date_parsed_tuple:
        try:
            return datetime(*date_parsed_tuple[:6])
        except Exception:
            pass
            
    if not date_str:
        return datetime.now()
        
    # Try parsing RFC 822/2822 dates (standard for RSS)
    try:
        dt_tuple = email.utils.parsedate_to_datetime(date_str)
        return dt_tuple.replace(tzinfo=None)
    except Exception:
        pass
        
    # Fallbacks for other formats
    for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%a, %d %b %Y %H:%M:%S'):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            pass
            
    return datetime.now()

def determine_category(title, summary, default_category):
    """
    Heuristically analyzes title and summary to categorize the research article.
    """
    text = f"{title} {summary}".lower()
    
    # Define keywords for categorization
    categories = {
        'Computer Vision': [
            'vision', 'image', 'object detection', 'segmentation', 'cnn', 'convolutional', 
            'diffusion model', 'gan', 'generative adversarial', 'pixels', 'video', 'depth estimation',
            'pose estimation', 'facial recognition', 'super-resolution', '3d reconstruction'
        ],
        'Natural Language Processing': [
            'language', 'nlp', 'translation', 'speech', 'text', 'transformer', 'llm', 'gpt', 
            'rag', 'retrieval-augmented', 'prompting', 'token', 'semantic', 'parsing', 'sentiment',
            'summarization', 'question answering', 'corpus', 'dialogue', 'lexical'
        ],
        'AI Ethics & Governance': [
            'governance', 'ethics', 'safety', 'alignment', 'bias', 'fairness', 'privacy',
            'regulation', 'deontic', 'policy', 'explainability', 'xai', 'interpretability',
            'censorship', 'copyright', 'hallucination', 'responsible ai'
        ],
        'Robotics & Control': [
            'robot', 'robotic', 'manipulator', 'drone', 'autonomous vehicle', 'navigation',
            'quadrotor', 'control system', 'trajectory', 'kinematics', 'actuator', 'locomotion'
        ],
        'Reinforcement Learning': [
            'reinforcement learning', 'rl', 'policy gradient', 'q-learning', 'markov decision', 
            'mdp', 'agent-based', 'reward function', 'actor-critic', 'multi-agent rl'
        ]
    }
    
    for cat, keywords in categories.items():
        if any(kw in text for kw in keywords):
            return cat
            
    # Fallback to feed default category if keyword match fails
    if default_category in ['Artificial Intelligence', 'Machine Learning']:
        # If it's a very broad default category, check if we can specify it
        if 'learning' in text or 'neural network' in text or 'deep learning' in text or 'dataset' in text:
            return 'Machine Learning'
        return 'Artificial Intelligence'
        
    return default_category

def fetch_feed_data():
    """
    Fetches and parses updates from configured RSS feeds.
    Eliminates duplicates and caches the sorted result.
    """
    all_items = []
    seen_links = set()
    
    for feed in FEEDS:
        try:
            logging.info(f"Fetching RSS feed: {feed['name']} - {feed['url']}")
            d = feedparser.parse(feed['url'])
            
            if d.bozo:
                logging.warning(f"Possible parsing issue with {feed['name']}: {d.bozo_exception}")
                
            entries = d.entries
            logging.info(f"Parsed {len(entries)} entries for {feed['name']}")
            
            for entry in entries:
                link = entry.get('link', '')
                if not link or link in seen_links:
                    continue
                
                seen_links.add(link)
                
                # Get titles and clean them
                raw_title = entry.get('title', 'No Title')
                title = clean_title(raw_title)
                
                # Get summary/description and clean it
                raw_summary = entry.get('summary', entry.get('description', entry.get('content', [{}])[0].get('value', '')))
                summary = clean_summary(raw_summary)
                
                # Parse date
                pub_date = parse_date(entry.get('published', entry.get('updated', '')), entry.get('published_parsed'))
                
                # Format authors
                authors_list = entry.get('authors', [])
                if authors_list:
                    authors = ", ".join([a.get('name', '') for a in authors_list if a.get('name')])
                elif entry.get('author'):
                    authors = entry.get('author')
                else:
                    authors = feed['source']
                
                # Categorize
                category = determine_category(title, summary, feed['default_category'])
                
                # Generate unique ID from link
                article_id = hashlib.md5(link.encode()).hexdigest()
                
                all_items.append({
                    'id': article_id,
                    'title': title,
                    'link': link,
                    'summary': summary,
                    'authors': authors,
                    'published': pub_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'published_raw': pub_date,
                    'category': category,
                    'source': feed['source'],
                    'feed_name': feed['name']
                })
        except Exception as e:
            logging.error(f"Error fetching feed {feed['name']}: {str(e)}")
            
    # Sort all items by publication date descending
    all_items.sort(key=lambda x: x['published_raw'], reverse=True)
    
    # Format date for UI display
    for item in all_items:
        # Convert published_raw to pretty date like "Jun 19, 2026"
        dt = item['published_raw']
        item['date_pretty'] = dt.strftime('%b %d, %Y')
        # Remove datetime object before serializing
        del item['published_raw']
        
    FEED_CACHE['items'] = all_items
    FEED_CACHE['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return all_items

# --- Smart Content Generator Heuristics ---

def split_into_sentences(text):
    """
    Helper to split clean text into clean sentences.
    """
    if not text:
        return []
    # Split on periods/exclamations/questions followed by space and capital letter/digit
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def extract_heuristics(title, summary):
    """
    Extracts structured parts of the paper using simple rule-based NLP heuristics.
    """
    sentences = split_into_sentences(summary)
    
    problem = ""
    solution = ""
    method = ""
    result = ""
    
    # Heuristic scoring arrays
    problem_triggers = ["however", "suffer from", "challenge", "limitation", "existing", "traditional", "costly", "difficult", "demanding", "restrictive", "lack of"]
    solution_triggers = ["we propose", "we present", "we introduce", "this paper", "this work", "our approach", "we develop", "we define", "in this study", "we create"]
    method_triggers = ["model", "framework", "architecture", "algorithm", "specifically", "by leveraging", "based on", "utilize", "incorporate", "technique"]
    result_triggers = ["show that", "outperform", "improves", "results", "demonstrate", "evaluation", "experimental", "achieve", "accuracy", "performance", "effective", "reduce"]
    
    # Helper to check triggers and assign sentences
    for s in sentences:
        s_lower = s.lower()
        if any(w in s_lower for w in problem_triggers) and not problem:
            problem = s
        elif any(w in s_lower for w in solution_triggers) and not solution:
            solution = s
        elif any(w in s_lower for w in method_triggers) and not method:
            method = s
        elif any(w in s_lower for w in result_triggers) and not result:
            result = s

    # Fallback cascade to populate empty slots
    if not problem and len(sentences) > 0:
        problem = sentences[0]
    if not solution:
        if len(sentences) > 1:
            solution = sentences[1]
        elif len(sentences) > 0:
            solution = sentences[0]
    if not method:
        # Pick the 3rd sentence or solution if only 1 sentence
        if len(sentences) > 2:
            method = sentences[2]
        else:
            method = solution
    if not result:
        # Check remaining sentences for result keywords
        for s in sentences[2:]:
            if any(w in s.lower() for w in ["achieve", "accuracy", "performance", "effective", "state-of-the-art"]):
                result = s
                break
        if not result and len(sentences) > 3:
            result = sentences[-1]
        elif not result:
            result = "The findings suggest a promising direction for future research in this domain."

    # Return trimmed sentences
    return {
        'problem': problem.strip(),
        'solution': solution.strip(),
        'method': method.strip(),
        'result': result.strip()
    }

def format_linkedin_post(title, authors, link, category, heuristics, tone):
    """
    Formats a LinkedIn post based on tone and extracted heuristics.
    """
    hashtag_cat = category.replace(" ", "").replace("&", "")
    hashtags = f"#AI #{hashtag_cat} #AIResearch #DeepLearning #TechInnovation"
    
    author_tag = f"by {authors}" if authors and authors != "arXiv" and authors != "MIT News" and authors != "Berkeley AI Research" else ""
    if len(author_tag) > 80:
        # Shorten authors if too long
        author_tag = author_tag[:77] + "..."

    problem = heuristics['problem']
    solution = heuristics['solution']
    method = heuristics['method']
    result = heuristics['result']

    if tone == 'professional':
        post = (
            f"🚀 AI research is moving at a break-neck pace. A new paper on **{title}** outlines "
            f"a significant step forward in {category}.\n\n"
            f"🔍 **The Challenge**:\n{problem}\n\n"
            f"💡 **The Innovation**:\n{solution}\n\n"
            f"⚡ **How It Works**:\n{method}\n\n"
            f"📈 **The Impact**:\n{result}\n\n"
            f"This represents a crucial advancement for researchers and practitioners in {category}. "
            f"Congrats to the authors {author_tag} on this valuable contribution!\n\n"
            f"🔗 Read the full research paper here: {link}\n\n"
            f"{hashtags} #MachineLearning"
        )
    elif tone == 'enthusiast':
        post = (
            f"🔥 This is fascinating! Just read through the latest AI research: **{title}**.\n\n"
            f"Here is the quick TL;DR of what this means for {category}:\n\n"
            f"👉 **The Problem:** {problem}\n"
            f"🧠 **The Solution:** {solution}\n"
            f"✨ **Why it matters:** {result}\n\n"
            f"Research is moving so fast right now. If you're building or researching in {category}, "
            f"this is definitely worth checking out. 📖\n\n"
            f"Check it out here: {link}\n\n"
            f"🚀 {hashtags} #GenerativeAI #TechTrends"
        )
    else:  # academic
        post = (
            f"📝 Literature Review Update: A close look at '**{title}**' {author_tag}.\n\n"
            f"This research makes important contributions to the subfield of {category}:\n\n"
            f"• **Theoretical Context**: {problem}\n"
            f"• **Proposed Methodology**: {solution}\n"
            f"• **Core Mechanics**: {method}\n"
            f"• **Empirical Validation**: {result}\n\n"
            f"The study offers robust pathways for addressing fundamental constraints in {category}.\n\n"
            f"📄 Full document access: {link}\n\n"
            f"{hashtags} #AcademicChatter #ComputerScience #NLP #CV"
        )
    return post

def format_exec_summary(title, authors, link, category, heuristics, tone):
    """
    Formats a professional Executive Summary based on tone and extracted heuristics.
    """
    author_str = f"Authors: {authors}" if authors else "Source: AI Research Update"
    problem = heuristics['problem']
    solution = heuristics['solution']
    method = heuristics['method']
    result = heuristics['result']

    intro = ""
    if tone == 'professional':
        intro = "This executive briefing highlights strategic research implications for business and technical leaders."
    elif tone == 'enthusiast':
        intro = "Here's a high-impact overview of a cool new technical approach in AI research."
    else:
        intro = "A formal scientific summary highlighting theoretical contributions and experimental results."

    summary = (
        f"EXECUTIVE SUMMARY: {title.upper()}\n"
        f"==================================================\n"
        f"{author_str} | Category: {category}\n"
        f"{intro}\n\n"
        f"1. BACKGROUND & PROBLEM STATEMENT\n"
        f"   {problem}\n\n"
        f"2. CORE INNOVATION & PROPOSED SOLUTION\n"
        f"   {solution}\n\n"
        f"3. METHODOLOGICAL APPROACH\n"
        f"   {method}\n\n"
        f"4. KEY FINDINGS & EMPIRICAL RESULTS\n"
        f"   {result}\n\n"
        f"5. STRATEGIC IMPLICATIONS\n"
        f"   This research suggests immediate applications in optimizing {category} workflows. "
        f"Organization should monitor these methodologies for integration in production environments.\n\n"
        f"--------------------------------------------------\n"
        f"Original Document Link: {link}\n"
    )
    return summary

def format_key_takeaways(title, authors, link, category, heuristics):
    """
    Formats key takeaways as structured bullet points.
    """
    author_str = f" ({authors})" if authors else ""
    takeaways = (
        f"📌 KEY TAKEAWAYS: {title}\n"
        f"Source: {link}{author_str}\n"
        f"Category: {category}\n"
        f"==================================================\n\n"
        f"• 🎯 **Core Objective**: To address constraints in {category}. Specifically: \"{heuristics['problem']}\"\n\n"
        f"• 🛠️ **Methodology / Innovation**: The paper introduces a novel approach: \"{heuristics['solution']}\"\n\n"
        f"• 🧩 **Key Mechanism**: \"{heuristics['method']}\"\n\n"
        f"• 📊 **Key Outcome / Result**: \"{heuristics['result']}\"\n\n"
        f"• 🚀 **Direct Application**: Practical deployment of these findings can significantly enhance performance and governance in {category} applications."
    )
    return takeaways

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/updates', methods=['GET'])
def get_updates():
    search_query = request.args.get('search', '').strip().lower()
    category_filter = request.args.get('category', '').strip()
    source_filter = request.args.get('source', '').strip()
    sort_order = request.args.get('sort', 'latest').strip()

    # Load cache if empty
    items = FEED_CACHE['items']
    if not items:
        logging.info("Cache is empty. Fetching feed data...")
        items = fetch_feed_data()
        
    filtered_items = items.copy()
    
    # Apply category filter
    if category_filter and category_filter.lower() != 'all':
        filtered_items = [item for item in filtered_items if item['category'].lower() == category_filter.lower()]
        
    # Apply source filter
    if source_filter and source_filter.lower() != 'all':
        filtered_items = [item for item in filtered_items if item['source'].lower() == source_filter.lower()]
        
    # Apply search query
    if search_query:
        filtered_items = [
            item for item in filtered_items if 
            search_query in item['title'].lower() or 
            search_query in item['summary'].lower() or 
            search_query in item['authors'].lower()
        ]
        
    # Apply sorting
    if sort_order == 'oldest':
        # Simple date sorting string-based is fine because formatted YYYY-MM-DD HH:MM:SS
        filtered_items.sort(key=lambda x: x['published'])
    elif sort_order == 'az':
        filtered_items.sort(key=lambda x: x['title'].lower())
    else:  # latest
        filtered_items.sort(key=lambda x: x['published'], reverse=True)
        
    # Extract unique categories and sources for the filter dropdowns dynamically
    categories = sorted(list(set(item['category'] for item in items)))
    sources = sorted(list(set(item['source'] for item in items)))
        
    return jsonify({
        'success': True,
        'count': len(filtered_items),
        'last_updated': FEED_CACHE['last_updated'],
        'items': filtered_items,
        'categories': categories,
        'sources': sources
    })

@app.route('/api/refresh', methods=['GET'])
def refresh_updates():
    logging.info("Forced refresh requested...")
    try:
        items = fetch_feed_data()
        categories = sorted(list(set(item['category'] for item in items)))
        sources = sorted(list(set(item['source'] for item in items)))
        return jsonify({
            'success': True,
            'count': len(items),
            'last_updated': FEED_CACHE['last_updated'],
            'items': items,
            'categories': categories,
            'sources': sources
        })
    except Exception as e:
        logging.error(f"Error during refresh: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/generate', methods=['POST'])
def generate_summary():
    data = request.json or {}
    title = data.get('title', '').strip()
    summary = data.get('summary', '').strip()
    authors = data.get('authors', '').strip()
    link = data.get('link', '').strip()
    category = data.get('category', '').strip()
    tone = data.get('tone', 'professional').strip() # professional, enthusiast, academic
    format_type = data.get('format', 'linkedin').strip() # linkedin, exec, takeaways

    if not title or not summary:
        return jsonify({
            'success': False,
            'error': 'Missing required fields: title and summary'
        }), 400

    try:
        # Extract components
        heuristics = extract_heuristics(title, summary)
        
        # Format based on format_type
        if format_type == 'linkedin':
            output = format_linkedin_post(title, authors, link, category, heuristics, tone)
        elif format_type == 'exec':
            output = format_exec_summary(title, authors, link, category, heuristics, tone)
        elif format_type == 'takeaways':
            output = format_key_takeaways(title, authors, link, category, heuristics)
        else:
            output = format_linkedin_post(title, authors, link, category, heuristics, tone)

        return jsonify({
            'success': True,
            'output': output
        })
    except Exception as e:
        logging.error(f"Error generating summary: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Prefetch data on startup
    logging.info("Prefetching feed data on startup...")
    try:
        fetch_feed_data()
    except Exception as e:
        logging.error(f"Failed to prefetch feeds on startup: {str(e)}")
        
    app.run(debug=True, port=5000)
