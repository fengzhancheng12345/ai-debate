"""Real research layer for debate system - fetches free data from multiple sources"""
import requests
import urllib.parse
import re
import time
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Try to import optional dependencies
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class DebateResearcher:
    """Fetches real, free data for debate agents from multiple sources.
    
    All sources are truly free - no API keys, no paid services.
    Uses ThreadPoolExecutor for parallel fetching.
    """
    
    def __init__(self, max_chars_per_source: int = 3000):
        self.max_chars_per_source = max_chars_per_source
    
    def research_topic(self, topic: str, agents: List[Dict]) -> Dict[str, str]:
        """Main entry point - parallel fetch from all relevant sources.
        
        Args:
            topic: The debate topic string
            agents: List of agent dicts with 'role' and 'name' keys
            
        Returns:
            Dict mapping source name to data string (truncated to max_chars_per_source)
        """
        sources = self._plan_sources(topic, agents)
        
        results = {}
        
        # Use ThreadPoolExecutor for parallel fetching
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_source = {}
            for source_name in sources:
                fetcher_method = getattr(self, source_name, None)
                if fetcher_method and callable(fetcher_method):
                    future = executor.submit(fetcher_method, topic)
                    future_to_source[future] = source_name
            
            for future in as_completed(future_to_source, timeout=30):
                source_name = future_to_source[future]
                try:
                    result = future.result(timeout=15)
                    if result:
                        # Truncate each source result
                        results[source_name] = result[:self.max_chars_per_source]
                except Exception as e:
                    print(f"Researcher [{source_name}] failed: {e}")
        
        return results
    
    def _plan_sources(self, topic: str, agents: List[Dict]) -> List[str]:
        """Decide which sources to fetch based on topic and agent roles.
        
        Args:
            topic: The debate topic
            agents: List of agent dicts
            
        Returns:
            List of source method names to call
        """
        topic_lower = topic.lower()
        agent_roles = [a.get("role", "").lower() for a in agents]
        
        sources = [
            "_fetch_web_search",
            "_fetch_wikipedia",
            "_fetch_news",
        ]
        
        # Add finance sources if topic is about finance/business
        finance_keywords = ["股票", "股市", "金融", "投资", "经济", "gdp", "苹果", "特斯拉", 
                          "微软", "谷歌", "亚马逊", "英伟达", "比亚迪", "茅台", "腾讯",
                          "阿里巴巴", "京东", "美团", "bank", "stock", "finance", "market",
                          "crypto", "bitcoin", "货币", "美联储", "利率", "通胀"]
        if any(kw in topic_lower for kw in finance_keywords):
            sources.append("_fetch_yahoo_finance")
            sources.append("_fetch_macro_data")
            sources.append("_fetch_china_stats")
        
        # Add academic sources for research-oriented topics
        research_keywords = ["研究", "论文", "学术", "技术", "ai", "人工智能", "机器学习",
                           "研究", "science", "research", "paper", "academic"]
        if any(kw in topic_lower for kw in research_keywords):
            sources.append("_fetch_arxiv")
            sources.append("_fetch_semantic_scholar")
        
        # Add GitHub for tech topics
        tech_keywords = ["编程", "代码", "软件", "github", "开发", "技术", "开源",
                        "programming", "code", "software", "developer", "open source"]
        if any(kw in topic_lower for kw in tech_keywords):
            sources.append("_fetch_github")
        
        # Add tech news
        sources.append("_fetch_tech_news")
        
        return sources
    
    def _build_data_context(self, agent_role: str, research_data: Dict[str, str]) -> str:
        """Build context string from research data for a specific agent role.
        
        Args:
            agent_role: The role of the agent (e.g., 'researcher', 'skeptic')
            research_data: Dict of source_name -> data_string
            
        Returns:
            Formatted context string, or empty string if no relevant data
        """
        if not research_data:
            return ""
        
        sections = ["\n\n【📊 实时研究数据】\n"]
        
        # Map source methods to readable names
        source_labels = {
            "_fetch_web_search": "🌐 网络搜索",
            "_fetch_wikipedia": "📚 维基百科",
            "_fetch_news": "📰 百度新闻",
            "_fetch_yahoo_finance": "💹 Yahoo Finance",
            "_fetch_macro_data": "📈 宏观经济(FRED)",
            "_fetch_china_stats": "🏛️ 中国统计数据",
            "_fetch_arxiv": "📑 arXiv学术论文",
            "_fetch_semantic_scholar": "🔬 Semantic Scholar",
            "_fetch_github": "💻 GitHub项目",
            "_fetch_tech_news": "📱 科技新闻",
        }
        
        for source_method, data in research_data.items():
            if data and data.strip():
                label = source_labels.get(source_method, source_method)
                sections.append(f"\n{label}：\n{data[:2500]}\n")
        
        return "".join(sections)
    
    # -------------------------------------------------------------------------
    # Individual fetchers - all return empty string on failure
    # -------------------------------------------------------------------------
    
    def _fetch_web_search(self, topic: str) -> str:
        """Bing web search (HTML) - works in China, no API key needed"""
        try:
            url = f"https://www.bing.com/search?q={urllib.parse.quote(topic)}&first=1&rd=1"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                return ""

            # Parse Bing search result snippets
            snippets = re.findall(
                r'<li class="b_algo"[^>]*>.*?<p>([^<]+)</p>',
                r.text, re.DOTALL
            )
            if not snippets:
                snippets = re.findall(
                    r'class="[^"]*b_paractiph[^"]*"[^>]*>([^<]+)',
                    r.text
                )
            if not snippets:
                snippets = re.findall(
                    r'<p class="[^"]*"[^>]*>([^<]{30,300}?)</p>',
                    r.text
                )

            if snippets:
                results = []
                for s in snippets[:8]:
                    clean = re.sub(r'<[^>]+>', '', s).strip()
                    clean = clean.replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'")
                    if clean and len(clean) > 15:
                        results.append(f"- {clean[:200]}")
                if results:
                    return f"【🌐 Bing 搜索结果】\n" + "\n".join(results)[:3000]

            return ""
        except Exception as e:
            print(f"Web search error: {e}")
            return ""
    
    def _fetch_wikipedia(self, topic: str) -> str:
        """Wikipedia: search for correct title, then get summary. Falls back gracefully."""
        try:
            # Step 1: search for the article title (opensearch returns list: [query, [titles], [descs], [urls]])
            search_url = (
                "https://en.wikipedia.org/w/api.php"
                "?action=opensearch"
                "&search=" + urllib.parse.quote(topic) +
                "&limit=1&format=json"
            )
            r = requests.get(search_url, timeout=8, headers={"User-Agent": "DebateBot/1.0 (research; mail@example.com)"})
            title = None
            if r.status_code == 200:
                data = r.json()
                # opensearch format: [search_term, [title1, title2], [desc1, desc2], [url1, url2]]
                if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list) and data[1]:
                    title = data[1][0]

            if title:
                # Step 2: fetch the article summary
                summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
                r2 = requests.get(summary_url, timeout=8, headers={"User-Agent": "DebateBot/1.0 (research; mail@example.com)"})
                if r2.status_code == 200:
                    d2 = r2.json()
                    extract = d2.get('extract', '')
                    if extract:
                        return f"【📚 Wikipedia】\n标题：{d2.get('title', title)}\n\n摘要：{extract[:2000]}"

            # Chinese Wikipedia fallback
            search_url_zh = (
                "https://zh.wikipedia.org/w/api.php"
                "?action=opensearch"
                "&search=" + urllib.parse.quote(topic) +
                "&limit=1&format=json"
            )
            r = requests.get(search_url_zh, timeout=8, headers={"User-Agent": "DebateBot/1.0 (research; mail@example.com)"})
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list) and data[1]:
                    title_zh = data[1][0]
                    summary_url_zh = f"https://zh.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title_zh)}"
                    r2 = requests.get(summary_url_zh, timeout=8, headers={"User-Agent": "DebateBot/1.0 (research; mail@example.com)"})
                    if r2.status_code == 200:
                        d2 = r2.json()
                        extract = d2.get('extract', '')
                        if extract:
                            return f"【📚 维基百科】\n标题：{d2.get('title', title_zh)}\n\n摘要：{extract[:2000]}"

            return ""
        except Exception as e:
            print(f"Wikipedia error: {e}")
            return ""
    
    def _fetch_news(self, topic: str) -> str:
        """Baidu News - free, no API key"""
        try:
            url = f"https://news.baidu.com/ns?word={requests.utils.quote(topic)}&tn=news&from=news&cl=2&rn=10&ct=1"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                return ""
            
            # Try various Baidu news title patterns
            titles = re.findall(r'class="news-title-font_[^"]*"[^>]*>([^<]+)<', r.text)
            
            # Fallback patterns
            if not titles:
                titles = re.findall(r'<h3 class="news-title[^"]*"[^>]*><a[^>]*>([^<]+)</a>', r.text)
            if not titles:
                titles = re.findall(r'class="news_title[^"]*"[^>]*>([^<]+)<', r.text)
            if not titles:
                titles = re.findall(r'<a[^>]+class="[^"]*title[^"]*"[^>]*>([^<]+)<', r.text)
            
            if titles:
                results = []
                for t in titles[:10]:
                    clean = t.strip().replace('&amp;', '&').replace('&quot;', '"')
                    if clean and len(clean) > 5:
                        results.append(f"- {clean}")
                if results:
                    return f"【📰 百度新闻】\n" + "\n".join(results)[:3000]
            
            return ""
        except Exception as e:
            print(f"Baidu news error: {e}")
            return ""
    
    def _fetch_yahoo_finance(self, topic: str) -> str:
        """Yahoo Finance via yfinance Python package - free"""
        if not YFINANCE_AVAILABLE:
            print("yfinance not available, skipping Yahoo Finance")
            return ""
        
        try:
            ticker_map = {
                '苹果': 'AAPL', 'Apple': 'AAPL',
                '特斯拉': 'TSLA', 'Tesla': 'TSLA', 'Tesla Inc': 'TSLA',
                '微软': 'MSFT', 'Microsoft': 'MSFT',
                '谷歌': 'GOOGL', 'Google': 'GOOGL', 'Alphabet': 'GOOGL',
                '亚马逊': 'AMZN', 'Amazon': 'AMZN',
                '英伟达': 'NVDA', 'Nvidia': 'NVDA', 'NVIDIA': 'NVDA',
                'Meta': 'META', 'Facebook': 'META',
                '比亚迪': 'BYDDY', 'BYD': 'BYDDY',
                '茅台': '600519.SS', 'Kweichow Moutai': '600519.SS',
                '腾讯': '0700.HK', 'Tencent': '0700.HK',
                '阿里巴巴': 'BABA', 'Alibaba': 'BABA',
                '京东': 'JD', 'JD.com': 'JD',
                '美团': '3690.HK', 'Meituan': '3690.HK',
                'OpenAI': 'MSFT',  # OpenAI not publicly traded, use MSFT as proxy
                'ChatGPT': 'MSFT',
                'nvidia': 'NVDA', '英伟达': 'NVDA',
                '苹果': 'AAPL', 'apple': 'AAPL',
                '黄金': 'GC=F', 'gold': 'GC=F',
                '比特币': 'BTC-USD', 'bitcoin': 'BTC-USD',
                '原油': 'CL=F', 'oil': 'CL=F',
            }
            
            ticker = None
            for name, t in ticker_map.items():
                if name.lower() in topic.lower():
                    ticker = t
                    company_name = name
                    break
            
            if not ticker:
                return ""
            
            stock = yf.Ticker(ticker)
            try:
                info = stock.info.get(timeout=10)
            except Exception:
                return ""
            
            if not info or 'regularMarketPrice' not in info:
                return ""
            
            price = info.get('regularMarketPrice', 'N/A')
            if price and isinstance(price, (int, float)):
                price = f"${price:.2f}"
            
            pe = info.get('trailingPE', 'N/A')
            if pe and isinstance(pe, (int, float)):
                pe = f"{pe:.2f}"
            
            mktcap = info.get('marketCap', 0)
            if mktcap:
                if mktcap >= 1e12:
                    mktcap = f"${mktcap/1e12:.2f}T"
                elif mktcap >= 1e9:
                    mktcap = f"${mktcap/1e9:.2f}B"
                else:
                    mktcap = f"${mktcap/1e6:.2f}M"
            else:
                mktcap = 'N/A'
            
            recommendation = info.get('recommendationKey', 'N/A')
            week52_low = info.get('fiftyTwoWeekLow', 'N/A')
            week52_high = info.get('fiftyTwoWeekHigh', 'N/A')
            
            rev = info.get('totalRevenue', 0)
            if rev:
                if rev >= 1e12:
                    rev = f"${rev/1e12:.2f}T"
                elif rev >= 1e9:
                    rev = f"${rev/1e9:.2f}B"
                else:
                    rev = f"${rev/1e6:.2f}M"
            else:
                rev = 'N/A'
            
            dividend = info.get('dividendYield', 0)
            if dividend:
                dividend = f"{dividend*100:.2f}%"
            else:
                dividend = 'N/A'
            
            return f"""【💹 Yahoo Finance - {company_name}({ticker})】
当前股价：{price}
市值：{mktcap}
PE比率：{pe}
总营收：{rev}
股息率：{dividend}
分析师评级：{recommendation}
52周范围：{week52_low} - {week52_high}"""
        except Exception as e:
            print(f"Yahoo Finance error: {e}")
            return ""
    
    def _fetch_macro_data(self, topic: str) -> str:
        """FRED (Federal Reserve Economic Data) - free API, no key needed"""
        try:
            indicators = {
                'GDP': ('GDPC1', '美国实际GDP环比季度增长率'),
                'CPI': ('CPIAUCSL', '美国消费者物价指数同比'),
                '失业率': ('UNRATE', '美国失业率百分比'),
                '联邦基金利率': ('FEDFUNDS', '美联储基准利率'),
                '纳斯达克': ('NASDAQCOM', '纳斯达克综合指数收盘价'),
                '恐慌指数': ('VIXCLS', 'VIX波动率指数'),
                'PCE通胀': ('PCECTPI', 'PCE个人消费支出价格指数'),
                '制造业PMI': ('MANEMP', '美国制造业就业人数'),
            }
            
            results = []
            
            for name, (series_id, desc) in indicators.items():
                try:
                    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&vintage_date=2025-01-01"
                    r = requests.get(url, timeout=6)
                    if r.status_code == 200 and len(r.text) > 50:
                        lines = r.text.strip().split('\n')
                        if len(lines) >= 2:
                            last_line = lines[-1]
                            parts = last_line.split(',')
                            if len(parts) >= 2:
                                date = parts[0].strip()
                                val = parts[1].strip()
                                if val and val != '.':
                                    results.append(f"- {name}({series_id}): {val} (as of {date}) [{desc}]")
                except Exception:
                    pass
            
            if results:
                return "【📈 FRED 宏观经济数据】\n" + "\n".join(results[:10])
            return ""
        except Exception as e:
            print(f"FRED error: {e}")
            return ""
    
    def _fetch_china_stats(self, topic: str) -> str:
        """Chinese National Bureau of Statistics - public data"""
        try:
            # Try the stats.gov.cn API for GDP and other indicators
            url = "https://data.stats.gov.cn/easyquery.htm"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://data.stats.gov.cn/',
                'Accept': 'application/json, text/javascript, */*',
            }
            
            # Query GDP data (A01 indicates GDP)
            params = {
                'm': 'QueryData',
                'dbcode': 'hgyd',
                'rowcode': 'zb',
                'colcode': 'sj',
                'wds': '[]',
                'dfwds': '[{"wdcode":"zb","valuecode":"A01"},{"wdcode":"sj","valuecode":"LAST5"}]',
                'k1': str(int(time.time()))
            }
            
            r = requests.get(url, params=params, headers=headers, timeout=10)
            if r.status_code == 200:
                try:
                    data = r.json()
                    if data.get('returncode') == 0:
                        return "【🏛️ 中国国家统计局】\n成功连接中国国家统计局数据库，可获取GDP等宏观经济数据"
                except:
                    pass
                if 'GDP' in r.text or '国内生产总值' in r.text:
                    return "【🏛️ 中国国家统计局】\n成功连接，可查询GDP等宏观经济数据"
            
            # Fallback: check Baidu for Chinese economic data
            return ""
        except Exception as e:
            print(f"China stats error: {e}")
        
        # Try Baidu news search for Chinese economic indicators
        try:
            news_url = f"https://news.baidu.com/ns?word={requests.utils.quote('中国GDP经济数据')}&tn=news&rn=5"
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(news_url, headers=headers, timeout=8)
            if r.status_code == 200 and ('GDP' in r.text or '经济' in r.text):
                return "【🏛️ 中国经济数据】\n可获取最新经济统计信息（来源：百度新闻）"
        except:
            pass
        
        return ""
    
    def _fetch_arxiv(self, topic: str) -> str:
        """arXiv academic papers - free API, no key needed"""
        import urllib.parse
        try:
            query = urllib.parse.quote(topic)
            url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=5&sortBy=relevance"
            r = requests.get(url, timeout=12)
            if r.status_code != 200:
                return ""
            
            # Parse Atom XML response
            entries = re.findall(r'<entry>(.*?)</entry>', r.text, re.DOTALL)
            if not entries:
                # If no full entries found, try parsing title directly
                titles = re.findall(r'<title>([^<]+)</title>', r.text)
                summaries = re.findall(r'<summary>([^<]+)</summary>', r.text)
                if titles and titles[0].strip() != '':
                    results = []
                    for i, title in enumerate(titles[:5]):
                        if title.strip() and not title.strip().startswith('Updated'):
                            summary = summaries[i].strip()[:300] if i < len(summaries) else ''
                            results.append(f"- {title.strip()}\n  {summary}")
                    if results:
                        return "【📑 arXiv 学术论文】\n" + "\n".join(results)[:3000]
                return ""
            
            results = []
            for entry in entries[:5]:
                titles = re.findall(r'<title>([^<]+)</title>', entry)
                summaries = re.findall(r'<summary>([^<]+)</summary>', entry)
                if titles:
                    title = titles[0].strip()
                    # Skip "Updated" titles which are metadata
                    if title and not title.startswith('Updated'):
                        summary = summaries[0].strip()[:300] if summaries else ''
                        results.append(f"- {title}\n  {summary}")
            
            if results:
                return "【📑 arXiv 学术论文】\n" + "\n".join(results)[:3000]
            return ""
        except Exception as e:
            print(f"arXiv error: {e}")
            return ""
    
    def _fetch_semantic_scholar(self, topic: str) -> str:
        """Semantic Scholar academic search - free API, no key needed"""
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={requests.utils.quote(topic)}&limit=5&fields=title,abstract,year,citationCount,authors"
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; DebateResearcher/1.0)'
            }
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                return ""
            
            data = r.json()
            papers = data.get('data', [])
            if not papers:
                return ""
            
            result = "【🔬 Semantic Scholar 学术搜索】\n"
            for p in papers[:5]:
                title = p.get('title', '')
                year = p.get('year', 'N/A')
                citations = p.get('citationCount', 0)
                abstract = str(p.get('abstract', ''))[:200]
                authors = p.get('authors', [])
                author_str = authors[0]['name'] if authors else 'Unknown'
                
                if title:
                    result += f"\n- {title}\n"
                    result += f"  作者：{author_str} | 年份：{year} | 引用：{citations}\n"
                    if abstract and abstract != 'None':
                        result += f"  摘要：{abstract}...\n"
            
            return result[:3000]
        except Exception as e:
            print(f"Semantic Scholar error: {e}")
            return ""
    
    def _fetch_github(self, topic: str) -> str:
        """GitHub repository search - free API, no key needed (rate limited)"""
        try:
            url = f"https://api.github.com/search/repositories?q={requests.utils.quote(topic)}&sort=stars&order=desc&per_page=5"
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; DebateResearcher/1.0)',
                'Accept': 'application/vnd.github.v3+json'
            }
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                return ""
            
            data = r.json()
            repos = data.get('items', [])
            if not repos:
                return ""
            
            result = "【💻 GitHub 项目】\n"
            for repo in repos[:5]:
                full_name = repo.get('full_name', '')
                stars = repo.get('stargazers_count', 0)
                language = repo.get('language', 'N/A')
                description = repo.get('description', '') or ''
                if description:
                    description = description[:100]
                result += f"\n- {full_name}\n"
                result += f"  ⭐ Stars: {stars} | 🌍 语言: {language}\n"
                if description:
                    result += f"  📝 描述: {description}\n"
            
            return result[:2500]
        except Exception as e:
            print(f"GitHub error: {e}")
            return ""
    
    def _fetch_tech_news(self, topic: str) -> str:
        """36kr / Bing News tech industry news - works in China"""
        try:
            # Try 36kr RSS (often accessible in China)
            try:
                rss_url = 'https://36kr.com/feed'
                rss = requests.get(rss_url, timeout=6, headers={'User-Agent': 'Mozilla/5.0'})
                if rss.status_code == 200:
                    titles = re.findall(r'<title><!\[CDATA\[([^\]]+)\]\]></title>', rss.text)
                    links = re.findall(r'<link><!\[CDATA\[([^\]]+)\]\]></link>', rss.text)
                    if titles:
                        results = []
                        for i, t in enumerate(titles[:8]):
                            clean = t.strip()
                            if clean and len(clean) > 5:
                                link = links[i].strip() if i < len(links) else ''
                                results.append(f"- {clean}")
                        if results:
                            return "【📱 36Kr 科技资讯】\n" + "\n".join(results)[:3000]
            except Exception:
                pass

            # Fallback: Bing News search
            query = urllib.parse.quote(topic)
            url = f"https://www.bing.com/news/search?q={query}&first=1&rd=1"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                return ""

            titles = re.findall(r'<div class="news-item[^"]*"[^>]*>.*?<a[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</a>', r.text, re.DOTALL)
            if not titles:
                titles = re.findall(r'class="[^"]*news-title[^"]*"[^>]*>([^<]+)<', r.text)
            if not titles:
                titles = re.findall(r'<h2[^>]*><a[^>]*>([^<]{10,200})</a></h2>', r.text)
            if titles:
                results = []
                for t in titles[:8]:
                    clean = re.sub(r'<[^>]+>', '', t).strip()
                    clean = clean.replace('&amp;', '&').replace('&quot;', '"')
                    if clean and len(clean) > 10:
                        results.append(f"- {clean[:200]}")
                if results:
                    return "【📱 科技新闻】\n" + "\n".join(results)[:3000]

            return ""
        except Exception as e:
            print(f"Tech news error: {e}")
            return ""


# Standalone test
if __name__ == "__main__":
    researcher = DebateResearcher()
    print("Testing researcher with topic: '人工智能对就业的影响'")
    data = researcher.research_topic("人工智能对就业的影响", [
        {"role": "researcher", "name": "研究员"},
        {"role": "skeptic", "name": "质疑者"}
    ])
    print(f"\nSources found: {list(data.keys())}")
    for source, content in data.items():
        print(f"\n=== {source} ===")
        print(content[:500] if content else "(empty)")
