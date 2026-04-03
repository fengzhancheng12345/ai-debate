"""Agent definitions and debate orchestration"""
import re
import uuid
import time
import json as json_module
from datetime import datetime
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass
from collections import Counter
from store import Message, DebateGroup, Agent, SessionStore, store
from researcher import DebateResearcher

import time

class DeepSeekClient:
    API_KEY = "sk-9d1169e00d184d1799e390d05e2c2e52"
    URL = "https://api.deepseek.com/chat/completions"

    def chat(self, messages, system="", max_tokens=8000):
        import requests
        headers = {"Authorization": f"Bearer {self.API_KEY}", "Content-Type": "application/json"}
        body = {"model": "deepseek-chat", "max_tokens": max_tokens, "messages": []}
        if system:
            body["messages"].append({"role": "system", "content": system})
        body["messages"].extend(messages)
        try:
            r = requests.post(self.URL, json=body, headers=headers, timeout=60)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            return f"[Error: DeepSeek {r.status_code}]"
        except Exception as e:
            return f"[Error: DeepSeek {e}]"

deepseek_client = DeepSeekClient()

def call_with_retry(messages, system="", client=None, max_retries=2):
    if client is None:
        from minimax import MiniMaxClient
        from config import MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL, MINIMAX_MAX_TOKENS, MINIMAX_TIMEOUT
        client = MiniMaxClient(MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL, MINIMAX_MAX_TOKENS, MINIMAX_TIMEOUT)
    
    for attempt in range(max_retries + 1):
        result = client.chat(messages, system=system)
        if result and not result.startswith("[Error:"):
            return result
        if attempt < max_retries:
            time.sleep(2 ** attempt)
    
    try:
        fallback = deepseek_client.chat(messages, system=system)
        if fallback and not fallback.startswith("[Error:"):
            return fallback
    except:
        pass
    return result if result else "[Error: All providers failed]"

# Default agents that the Main Planner can use as templates
DEFAULT_AGENT_TEMPLATES = {
    "researcher": {
        "name": "研究员",
        "emoji": "🔬",
        "color": "#3b82f6",
        "role": "researcher",
        "description": "深入研究话题，提供事实和数据支持的观点",
    },
    "skeptic": {
        "name": "质疑者",
        "emoji": "🤔",
        "color": "#f97316",
        "role": "skeptic", 
        "description": "从批判性角度分析，找出观点的漏洞和风险",
    },
    "optimist": {
        "name": "乐观派",
        "emoji": "🌟",
        "color": "#22c55e",
        "role": "optimist",
        "description": "从积极正面的角度分析，强调机遇和好处",
    },
    "realist": {
        "name": "务实派",
        "emoji": "⚖️",
        "color": "#a855f7",
        "role": "realist",
        "description": "从实际可行性角度分析，权衡利弊",
    },
    "critic": {
        "name": "批评家",
        "emoji": "🛡️",
        "color": "#ef4444",
        "role": "critic",
        "description": "提出反对意见和潜在问题",
    },
    "synthesizer": {
        "name": "综合分析师",
        "emoji": "🧠",
        "color": "#06b6d4",
        "role": "synthesizer",
        "description": "整合各方观点，找出共同点和分歧",
    },
    "historian": {
        "name": "历史视角",
        "emoji": "📜",
        "color": "#f59e0b",
        "role": "historian",
        "description": "从历史案例和经验中寻找参照",
    },
    "futurist": {
        "name": "未来学家",
        "emoji": "🚀",
        "color": "#8b5cf6",
        "role": "futurist",
        "description": "从未来趋势和可能性角度分析",
    },
}

def build_agent_prompt(agent: Dict, topic: str, conversation_history: str = "", round_num: int = 1, phase: str = "debate") -> tuple:
    """Build system prompt and user prompt for an agent"""
    role = agent["role"]
    name = agent["name"]
    emoji = agent["emoji"]
    desc = agent["description"]
    
    system = f"""你是一个被人格化的AI角色参与辩论。
你的身份：{name} {emoji}
角色描述：{desc}

核心原则：
1. 你是真实参与的，不是模拟的
2. 必须用中文回答，内容要有深度和价值
3. 可以参考对话历史中其他人的观点来回应
4. 保持角色一致性，不要偏离你的角色定位
5. 回复要有实质性内容，至少100字以上
6. 不要说"作为AI"之类的话，你就是你这个角色"""

    if phase == "debate":
        if conversation_history:
            user = f"""【辩题】
{topic}

【对话历史】（这是其他参与者的观点，请结合这些来回应）
{conversation_history}

【你的任务】
作为{name}，请围绕上述辩题，结合对话历史中其他人的观点，发表你的深度见解。

要求：
- 至少100字
- 可以同意或反对其他人的观点，但要给出理由
- 不要重复别人已经说过的内容，要提出新的视角
- 用中文回复

{name}的发言："""
        else:
            user = f"""【辩题】
{topic}

【你的任务】
作为{name}，请围绕上述辩题发表你的深度见解。

要求：
- 至少100字
- 提出有价值的观点和论据
- 用中文回复

{name}的发言："""
    elif phase == "vote":
        options = "支持 / 反对 / 中立（不表态）"
        if conversation_history:
            user = f"""【辩题】
{topic}

【对话历史】
{conversation_history}

【你的最终立场】
经过上面的讨论，作为{name}，你的最终立场是什么？

请明确表态：{options}
并简要说明原因（50字以内）

你的立场："""
        else:
            user = f"""【辩题】
{topic}

【你的最终立场】
作为{name}，你的最终立场是什么？

请明确表态：{options}
并简要说明原因（50字以内）

你的立场："""
    
    return system, user

def extract_vote(text: str) -> str:
    """Extract vote from agent response"""
    text_lower = text.lower()
    if "支持" in text_lower or "同意" in text_lower or "赞成" in text_lower:
        return "支持"
    elif "反对" in text_lower or "拒绝" in text_lower or "否定" in text_lower:
        return "反对"
    else:
        return "中立"

def _fallback_plan(topic: str) -> dict:
    """Fallback plan if planner fails to return JSON"""
    return {
        "groups": [
            {
                "name": "理性分析组",
                "description": "从逻辑和事实角度分析话题",
                "agents": [
                    {"key": "researcher", "name": "研究员", "emoji": "🔬", "color": "#3b82f6", "role": "researcher", "description": "深入研究", "prompt_hint": "从事实和数据角度分析"},
                    {"key": "skeptic", "name": "质疑者", "emoji": "🤔", "color": "#f97316", "role": "skeptic", "description": "批判分析", "prompt_hint": "找出潜在问题和风险"},
                    {"key": "synthesizer", "name": "综合分析师", "emoji": "🧠", "color": "#06b6d4", "role": "synthesizer", "description": "整合分析", "prompt_hint": "综合各方观点"},
                ]
            },
            {
                "name": "情感视角组",
                "description": "从情感和人文角度分析话题",
                "agents": [
                    {"key": "optimist", "name": "乐观派", "emoji": "🌟", "color": "#22c55e", "role": "optimist", "description": "积极视角", "prompt_hint": "从正面角度分析优点和机会"},
                    {"key": "realist", "name": "务实派", "emoji": "⚖️", "color": "#a855f7", "role": "realist", "description": "务实分析", "prompt_hint": "从可行性角度权衡利弊"},
                    {"key": "futurist", "name": "未来学家", "emoji": "🚀", "color": "#8b5cf6", "role": "futurist", "description": "未来视角", "prompt_hint": "从发展趋势角度分析"},
                ]
            }
        ],
        "total_rounds": 3,
        "discussion_focus": "全面深入讨论"
    }

def _build_history(messages: List[Message]) -> str:
    """Build conversation history text from messages"""
    if not messages:
        return ""
    lines = []
    for msg in messages:
        lines.append(f"【{msg.agent_name}】{msg.content}")
    return "\n\n".join(lines)

def _build_full_summary(session, topic: str, all_votes: dict) -> str:
    """Build comprehensive input for main planner's final synthesis"""
    lines = [f"# 辩题：{topic}\n"]
    lines.append(f"# 用户补充：{session.user_input}\n")
    lines.append(f"# 辩论轮次：{session.total_rounds}\n")
    
    for group in session.groups:
        lines.append(f"\n## {group.name}（{group.description}）")
        for msg in group.messages:
            lines.append(f"\n[{msg.agent_name}] {msg.content}")
        
        votes = [f"{a.name}={a.vote}" for a in group.agents]
        lines.append(f"\n投票结果：{', '.join(votes)}")
        lines.append(f"小组共识：{group.group_vote}")
    
    lines.append(f"\n## 所有投票汇总")
    for key, vote_info in all_votes.items():
        lines.append(f"- {vote_info['group']}/{vote_info['agent']}: {vote_info['vote']}")
    
    return "\n".join(lines)



def build_debate_context(topic: str, user_input: str) -> str:
    """Build rich context from structured user input fields"""
    if not user_input:
        return ""
    
    lines = []
    
    # Parse structured fields
    current_section = None
    section_content = []
    
    for line in user_input.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Check if it's a field header
        if line.startswith('【') and line.endswith('】'):
            # Save previous section
            if current_section and section_content:
                lines.append(f"{current_section}：{'；'.join(section_content)}")
            current_section = line[1:-1]  # Remove 【】
            section_content = []
        elif current_section:
            section_content.append(line)
        else:
            section_content.append(line)
    
    # Save last section
    if current_section and section_content:
        lines.append(f"{current_section}：{'；'.join(section_content)}")
    
    if not lines:
        return f"用户补充信息：{user_input}"
    
    return "\n".join(lines)


def run_debate_stream(session_id: str, client):
    """Main debate orchestrator - sync generator.
    
    Takes session_id (str) and client (MiniMaxClient instance).
    Yields dicts with event data. Uses client.chat() synchronously (no async/await).
    """
    session = store.get_session(session_id)
    if not session:
        yield {"type": "error", "data": {"message": "Session not found"}}
        return
    
    topic = session.topic
    user_input = session.user_input
    
    # Step 1: Planning phase
    yield {"type": "phase", "data": {"phase": "planning", "title": "主策划分析中..."}}
    
    # Call the planner (Main Planner LLM) to design debate groups
    

    # Build rich context for the planner
    rich_context = build_debate_context(topic, user_input)

    planner_prompt = f"""用户话题：{topic}
{rich_context}

你是一个专业的辩论策划专家，擅长将复杂话题拆解成多角度的辩论小组。
你的核心任务是：根据用户提供的信息，设计最合适的辩论结构。

## 设计原则

1. **角色要贴合用户背景**
   - 如果用户提供了个人情况（资金、偏好、条件等），角色设定要针对这些具体信息来设计
   - 如果用户提供了讨论角度，角色要覆盖这些角度
   - 如果用户有明确立场，辩论要针对这个立场展开论证或反驳

2. **小组设计要精准**
   - 通用话题：2-3个小组，覆盖不同视角（支持/质疑/综合）
   - 需要数据的热门话题（如电车、投资、科技）：优先安排需要数据的分析师角色
   - 个人决策类话题（如买车、买房）：设计了解用户情况的顾问角色
   - 争议话题（如政策、伦理）：设计正反方小组

3. **JSON要包含足够信息**
   - 每组3-5个角色
   - 每个角色要有针对性描述，不是泛泛的"分析师"
   - 总轮次2-3轮

请严格按照JSON格式回答，不要输出其他内容：
{{
  "groups": [
    {{
      "name": "小组名称",
      "description": "小组讨论方向",
      "agents": [
        {{"key": "unique_key", "name": "角色名", "emoji": "emoji", "color": "#hexcolor", "role": "role_key", "description": "角色描述", "prompt_hint": "具体讨论角度"}}
      ]
    }}
  ],
  "total_rounds": 3,
  "discussion_focus": "本轮讨论的重点"
}}"""
    planner_response = call_with_retry(
            [{"role": "user", "content": planner_prompt}],
            system="你是一个辩论策划专家，输出纯JSON。",
            client=client
        )

    yield {"type": "planner_message", "data": {"content": planner_response[:300] if planner_response else "策划完成"}}
    
    # Parse groups from planner response
    try:
        m = re.search(r'\{.*\}', planner_response, re.DOTALL)
        plan = json_module.loads(m.group()) if m else None
    except:
        plan = None
    
    if plan and "groups" in plan:
        groups_data = plan["groups"]
    else:
        groups_data = [
            {"name": "理性分析组", "description": "从逻辑和事实角度分析", "agents": [
                {"key": "researcher", "name": "研究员", "emoji": "🔬", "color": "#3b82f6", "role": "researcher", "description": "研究员", "prompt_hint": "从事实和数据角度深入分析"},
                {"key": "skeptic", "name": "质疑者", "emoji": "🤔", "color": "#f97316", "role": "skeptic", "description": "质疑者", "prompt_hint": "找出观点的漏洞和潜在风险"},
                {"key": "synthesizer", "name": "综合分析师", "emoji": "🧠", "color": "#06b6d4", "role": "synthesizer", "description": "综合分析师", "prompt_hint": "整合各方观点形成结论"},
            ]},
            {"name": "情感视角组", "description": "从情感和人本角度分析", "agents": [
                {"key": "optimist", "name": "乐观派", "emoji": "🌟", "color": "#22c55e", "role": "optimist", "description": "乐观派", "prompt_hint": "从积极正面角度分析机遇和好处"},
                {"key": "realist", "name": "务实派", "emoji": "⚖️", "color": "#a855f7", "role": "realist", "description": "务实派", "prompt_hint": "从实际可行性角度权衡利弊"},
                {"key": "futurist", "name": "未来学家", "emoji": "🚀", "color": "#8b5cf6", "role": "futurist", "description": "未来学家", "prompt_hint": "从未来趋势角度分析可能性"},
            ]},
        ]
    
    session.total_rounds = plan.get("total_rounds", 3) if plan else 3
    
    # Create group objects
    for group_data in groups_data:
        group = DebateGroup(
            id=str(uuid.uuid4())[:8],
            name=group_data["name"],
            description=group_data.get("description", ""),
            agents=[],
            max_rounds=session.total_rounds
        )
        for agent_data in group_data.get("agents", []):
            agent = Agent(
                key=agent_data["key"],
                name=agent_data["name"],
                emoji=agent_data.get("emoji", "💬"),
                color=agent_data.get("color", "#6366f1"),
                role=agent_data.get("role", "researcher"),
                prompt_template=agent_data.get("prompt_hint", "")
            )
            group.agents.append(agent)
        session.groups.append(group)
    
    yield {"type": "groups_created", "data": {
        "groups": [{"id": g.id, "name": g.name, "description": g.description, "agents": [
            {"key": a.key, "name": a.name, "emoji": a.emoji, "color": a.color}
            for a in g.agents
        ]} for g in session.groups]
    }}
    
    # Step 1.5: Research phase - fetch real data from multiple sources
    yield {"type": "phase", "data": {"phase": "researching", "title": "正在收集真实资料..."}}
    
    researcher = DebateResearcher()
    agent_roles = [{"role": a.role, "name": a.name} for g in session.groups for a in g.agents]
    research_data = researcher.research_topic(topic, agent_roles)
    
    yield {"type": "research_complete", "data": {
        "sources": list(research_data.keys()),
        "source_count": len(research_data)
    }}
    
    # Build research context for agents
    def build_research_context(agent_role: str, research_data: Dict[str, str]) -> str:
        """Build context string from research data for a specific agent role."""
        if not research_data:
            return ""
        
        sections = ["\n\n【📊 实时研究数据】\n以下是收集到的真实资料，请结合这些数据来论证你的观点：\n"]
        
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
    
    # Step 2: Debate rounds
    for round_num in range(1, session.total_rounds + 1):
        yield {"type": "round_start", "data": {"round": round_num, "title": f"第 {round_num} 轮讨论"}}
        
        for group in session.groups:
            yield {"type": "group_start", "data": {"group_id": group.id, "group_name": group.name}}
            
            # Build conversation history
            history_lines = []
            for msg in group.messages:
                history_lines.append(f"【{msg.agent_name}】{msg.content}")
            history_text = "\n\n".join(history_lines)
            
            for agent in group.agents:
                # Build the debate prompt with research context injected
                research_context = build_research_context(agent.role, research_data)
                
                # Build the debate prompt
                if history_text:
                    debate_prompt = f"""{research_context}

【辩题】
{topic}

【对话历史】（其他参与者的观点，请结合这些来回应）
{history_text}

【你的任务】
作为{agent.name}，请围绕上述辩题，结合对话历史中其他人的观点，发表你的深度见解。
要求：
- 至少150字，要有实质性内容
- 可以同意或反对其他人的观点，但必须给出具体理由
- 不要重复别人已经说过的内容，要提出新的视角
- 用中文回复

{agent.name}的发言："""
                else:
                    debate_prompt = f"""{research_context}

【辩题】
{topic}

【你的任务】
作为{agent.name}，请围绕上述辩题发表你的深度见解。
要求：
- 至少150字，要有实质性内容
- 提出有价值的观点和具体论据
- 用中文回复

{agent.name}的发言："""
                
                system_prompt = f"""你是一个被人格化的AI角色参与辩论。
你的身份：{agent.name} {agent.emoji}
角色描述：{agent.role}

核心原则：
1. 你是真实参与的，不是模拟的
2. 必须用中文回答，内容要有深度和价值
3. 可以结合对话历史中其他人的观点来回应
4. 保持角色一致性，不要偏离你的角色定位
5. 回复要有实质性内容，至少150字以上
6. 不要说"作为AI"之类的话，你就是你这个角色"""
                
                yield {"type": "agent_start", "data": {
                    "group_id": group.id,
                    "agent_key": agent.key,
                    "agent_name": agent.name,
                    "emoji": agent.emoji,
                    "color": agent.color,
                    "round": round_num
                }}
                
                # Call MiniMax synchronously
                response = call_with_retry(
                    [{"role": "user", "content": debate_prompt}],
                    system=system_prompt,
                    client=client
                )
                
                # Store the message
                msg = Message(
                    id=str(uuid.uuid4())[:8],
                    agent_key=agent.key,
                    agent_name=agent.name,
                    role="assistant",
                    content=response
                )
                group.messages.append(msg)
                
                yield {"type": "agent_message", "data": {
                    "group_id": group.id,
                    "agent_key": agent.key,
                    "agent_name": agent.name,
                    "content": response,
                    "round": round_num
                }}
                
                yield {"type": "agent_done", "data": {
                    "group_id": group.id,
                    "agent_key": agent.key,
                    "round": round_num
                }}
                
                # Update history for next agent in same group
                history_lines.append(f"【{agent.name}】{response}")
                history_text = "\n\n".join(history_lines)
    
    # Step 3: Voting
    yield {"type": "phase", "data": {"phase": "voting", "title": "各小组投票中"}}
    
    all_votes = {}
    for group in session.groups:
        yield {"type": "group_voting", "data": {"group_id": group.id, "group_name": group.name}}
        
        # Build debate summary for voting
        summary_lines = [f"辩题：{topic}\n"]
        for msg in group.messages:
            summary_lines.append(f"【{msg.agent_name}】{msg.content}")
        summary_text = "\n\n".join(summary_lines)
        
        for agent in group.agents:
            vote_prompt = f"""【辩题】
{topic}

【辩论总结】
{summary_text}

【你的任务】
经过上面的讨论，作为{agent.name}，你的最终立场是什么？

请明确表态：支持 / 反对 / 中立
并简要说明原因（50字以内）

你的立场："""
            
            system_prompt = f"""你是一个被人格化的AI角色。
你的身份：{agent.name} {agent.emoji}

请直接给出你的立场：支持、反对或中立，并用中文说明原因（50字以内）。"""
            
            response = call_with_retry(
                [{"role": "user", "content": vote_prompt}],
                system=system_prompt,
                client=client
            )
            
            # Extract vote from response
            text = response.lower()
            if "支持" in text or "同意" in text or "赞成" in text:
                vote = "支持"
            elif "反对" in text or "拒绝" in text or "否定" in text:
                vote = "反对"
            else:
                vote = "中立"
            
            agent.vote = vote
            agent.vote_reason = response[:200]
            all_votes[f"{group.id}_{agent.key}"] = {
                "agent": agent.name,
                "group": group.name,
                "vote": vote,
                "reason": response[:200],
                "emoji": agent.emoji
            }
            
            yield {"type": "vote_cast", "data": {
                "group_id": group.id,
                "agent_key": agent.key,
                "agent_name": agent.name,
                "vote": vote,
                "reason": response[:200]
            }}
        
        # Group consensus
        votes = [a.vote for a in group.agents if a.vote]
        if votes:
            counter = Counter(votes)
            group.group_vote = counter.most_common(1)[0][0]
        
        yield {"type": "group_vote_result", "data": {
            "group_id": group.id,
            "group_name": group.name,
            "group_vote": group.group_vote,
            "votes": {a.key: a.vote for a in group.agents}
        }}
    
    # Step 4: Main Planner final synthesis
    yield {"type": "phase", "data": {"phase": "summarizing", "title": "主策划综合分析中..."}}
    
    # Build full summary input
    full_lines = [f"# 辩题：{topic}\n"]
    for g in session.groups:
        full_lines.append(f"\n## {g.name}（{g.description}）")
        for msg in g.messages:
            full_lines.append(f"\n【{msg.agent_name}】{msg.content}")
        votes_str = ", ".join([f"{a.name}={a.vote}" for a in g.agents])
        full_lines.append(f"\n投票：{votes_str}，共识：{g.group_vote}")
    
    full_summary_input = "".join(full_lines)
    
    synthesis_prompt = f"""{full_summary_input}

请作为辩论总结专家，写出详尽的最终总结报告，要求：
1. 总结各小组的核心观点（100字以上）
2. 分析各方主要分歧
3. 找出各方共识点
4. 给出你的最终建议（100字以上，要有实质性内容）

用中文回复，至少300字。格式不限，但要结构清晰。"""
    
    synthesis_system = "你是一个辩论总结专家，擅长综合各方观点，给出平衡且有深度的结论。"
    
    final_summary = call_with_retry(
        [{"role": "user", "content": synthesis_prompt}],
        system=synthesis_system,
        client=client
    )
    
    session.final_answer = final_summary
    session.current_phase = "done"
    session.status = "completed"
    
    yield {"type": "final_answer", "data": {
        "topic": topic,
        "summary": final_summary,
        "votes": all_votes,
        "groups_summary": [
            {
                "name": g.name,
                "vote": g.group_vote,
                "members": [{"name": a.name, "vote": a.vote, "emoji": a.emoji} for a in g.agents]
            }
            for g in session.groups
        ]
    }}
    
    yield {"type": "complete", "data": {"session_id": session_id}}
    
    # Cleanup after a delay
    time.sleep(5)
    store.delete_session(session_id)
