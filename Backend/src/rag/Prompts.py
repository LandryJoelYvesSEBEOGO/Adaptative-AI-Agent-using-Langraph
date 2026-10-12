# Ajoutez ces imports en haut du fichier
from config.Config import Config
from src.core.few_shot_examples import select_similar_examples, format_few_shot_examples
from src.core.prompt_templates import (
    get_role_prompt, detect_role_from_question,
    get_chain_of_thought_instruction,
    format_structured_output_instruction
)

# Modifiez le prompt RAG dans get_prompts():
def get_prompts(
    router_instructions=None,
    doc_grader_instructions=None,
    doc_grader_prompt=None,
    rag_prompt=None,
    hallucination_grader_instructions=None,
    hallucination_grader_prompt=None,
    answer_grader_instructions=None,
    answer_grader_prompt=None,
    Rewritting_prompt=None,
    multi_criteria_grader_instructions=None,
    multi_criteria_grader_prompt=None,
    answer_quality_scorer_instructions=None,  
    answer_quality_scorer_prompt=None,
    question=None,  # Nouveau paramètre pour few-shot et role detection
):
    """
    Génère et retourne un ensemble de prompts pour différentes étapes.
    
    Args:
        question: Question de l'utilisateur (pour few-shot et role detection)
        ... (autres paramètres existants)
    """
    
    # Détecter le rôle si nécessaire
    role_key = None
    if question and getattr(Config, 'ROLE_BASED_PROMPTING_ENABLED', True):
        role_key = detect_role_from_question(question)
    
    role_prefix = get_role_prompt(role_key) if role_key else ""
    
    # Sélectionner les exemples few-shot
    few_shot_examples = []
    few_shot_text = ""
    if question and getattr(Config, 'FEW_SHOT_ENABLED', True):
        num_examples = getattr(Config, 'FEW_SHOT_NUM_EXAMPLES', 2)
        few_shot_examples = select_similar_examples(question, num_examples)
        few_shot_text = format_few_shot_examples(few_shot_examples)
    
    # Instruction Chain-of-Thought
    cot_instruction = ""
    if question:
        cot_instruction = get_chain_of_thought_instruction(question)
    
    # Instruction Structured Output
    structured_output = format_structured_output_instruction()
    
    prompts = {
        # Router Instructions
        "router_instructions": router_instructions or """You are an expert at routing a user question to a vectorstore or web search.
        The vectorstore contains annual (10-K) and quarterly (10-Q) financial reports of
        publicly listed companies (income statements, balance sheets, cash flows, risk factors,
        management discussion, segment results, etc.).

        Use the vectorstore for questions about the financial performance, accounting figures,
        business segments, risks or disclosures of companies. For all else, and especially for
        current events or recent market news, use web-search.
        Return JSON with a single key, 'datasource', that is either 'websearch' or 'vectorstore' depending on the question.""",

        # Retrieval Grader
        "doc_grader_instructions": doc_grader_instructions or """You are a grader assessing relevance of a retrieved document to a user question.
        If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant.""",

        "doc_grader_prompt": doc_grader_prompt or """Here is the retrieved document: \n\n {document} \n\n Here is the user question: \n\n {question}.
        Carefully and objectively assess whether the document contains at least some information that is relevant to the question.
        Return JSON with a single key, 'binary_score', that is either 'yes' or 'no' to indicate relevance.""",

        # RAG Prompt (MODIFIÉ)
        "rag_prompt": rag_prompt or (
            f"""{role_prefix}You are an assistant for question-answering tasks. 
{few_shot_text}{cot_instruction}{structured_output}Here is the context to use to answer the question:\n\n{{context}} 
Think carefully about the above context. 
Now, review the user question:\n\n{{question}}
Provide an answer to this question using only the above context. 
Use three sentences maximum and keep the answer concise.

IMPORTANT: When referencing information from the context, cite your sources using the format [1], [2], [3], etc., where the number corresponds to the document number in the context above.
For example: "Python is a programming language [1] that supports multiple paradigms [2]."

Answer:"""
        ),

        # Hallucination Grader
        "hallucination_grader_instructions": hallucination_grader_instructions or """You are a teacher grading a quiz. 
        You will be given FACTS and a STUDENT ANSWER. 

        Grading criteria:
        (1) Ensure the STUDENT ANSWER is grounded in the FACTS. 
        (2) Ensure the STUDENT ANSWER does not contain "hallucinated" information outside the scope of the FACTS.

        Score:
        - 'yes' means the answer meets all criteria.
        - 'no' means it does not.
        
        Explain your reasoning step by step. Avoid stating the correct answer outright.""",

        "hallucination_grader_prompt": hallucination_grader_prompt or """FACTS:\n\n {documents} \n\n STUDENT ANSWER: {generation}.
        Return JSON with two keys:
        - 'binary_score': 'yes' or 'no' indicating whether the STUDENT ANSWER is grounded in the FACTS.
        - 'explanation': an explanation of the score.""",

        # Answer Grader
        "answer_grader_instructions": answer_grader_instructions or """You are a teacher grading a quiz.
        You will be given a QUESTION and a STUDENT ANSWER. 

        Grading criteria:
        (1) The STUDENT ANSWER should adequately answer the QUESTION.
        
        Score:
        - 'yes' means the answer meets the criteria (it may contain extra information not explicitly asked for).
        - 'no' means the answer does not meet the criteria.
        
        Explain your reasoning step by step. Avoid stating the correct answer outright.""",

        "answer_grader_prompt": answer_grader_prompt or """QUESTION:\n\n {question} \n\n STUDENT ANSWER: {generation}.
        Return JSON with two keys:
        - 'binary_score': 'yes' or 'no' indicating whether the STUDENT ANSWER meets the criteria.
        - 'explanation': an explanation of the score.""",

        # Rewritting Prompt
        "Rewritting_prompt": Rewritting_prompt or """"
            You are a rewriting assistant. Your task is to take the user’s QUERY and conversation HISTORY and rewrite the query so that it is clear, explicit, and standalone.
            
            Conversation HISTORY (may be empty):
            {history}
            
            User QUERY:
            {query}
            
            Rewrite the query so it can be understood without the history. 
            - Preserve the original meaning.
            - Use the history to resolve references (e.g., "it", "that", "in 2022").
            - Improve grammar, structure, and clarity.
            - Return only the rewritten query, without additional commentary.

            Please provide your rewritten version of the query below:
            """,
        # Multi-Criteria Document Grader Instructions
        "multi_criteria_grader_instructions": multi_criteria_grader_instructions or """You are an expert grader assessing document relevance using multiple criteria.

Evaluate each document on 5 dimensions (0.0 to 1.0):
1. RELEVANCE: How semantically relevant is the document to the question? (0.0 = not relevant, 1.0 = highly relevant)
2. COVERAGE: How well does the document cover/address the question? (0.0 = no coverage, 1.0 = complete coverage)
3. FRESHNESS: How recent/fresh is the information? (0.0 = outdated, 1.0 = very recent) - Use 0.7 if date unknown
4. AUTHORITY: How authoritative/trustworthy is the source? (0.0 = unreliable, 1.0 = highly authoritative) - Use 0.7 if unknown
5. CLARITY: How clear and well-structured is the content? (0.0 = unclear, 1.0 = very clear)

Return a JSON object with:
- 'scores': object with keys 'relevance', 'coverage', 'freshness', 'authority', 'clarity' (each 0.0-1.0)
- 'overall_score': weighted average (float 0.0-1.0)
- 'accepted': boolean indicating if document should be used (based on threshold >= 0.6)
- 'reasoning': brief explanation of the scores (2-3 sentences)""",

        "multi_criteria_grader_prompt": multi_criteria_grader_prompt or """Here is the retrieved document:
{document}

Here is the user question:
{question}

Evaluate the document on all 5 criteria and provide detailed scores. Consider:
- RELEVANCE: Does the document directly relate to the question topic?
- COVERAGE: Does it answer parts of or the full question?
- FRESHNESS: Is the information current? (Estimate if date not provided)
- AUTHORITY: Is the source credible? (Infer from domain/context if not explicit)
- CLARITY: Is the content easy to understand and well-organized?

Return a JSON object with the structure specified in the instructions.""",
        # Answer Quality Scorer Instructions
        "answer_quality_scorer_instructions": answer_quality_scorer_instructions or """You are an expert evaluator assessing the quality of a generated answer.

Evaluate the answer on 5 dimensions (0.0 to 1.0):
1. RELEVANCE: Does the answer directly address and answer the question? (0.0 = not relevant, 1.0 = highly relevant)
2. COMPLETENESS: Does the answer provide complete information to fully address the question? (0.0 = incomplete, 1.0 = complete)
3. CONCISENESS: Is the answer concise without unnecessary verbosity? (0.0 = too verbose, 1.0 = perfectly concise)
4. ACCURACY: Is the answer factually accurate based on the provided context? (0.0 = inaccurate, 1.0 = highly accurate)
5. COHERENCE: Is the answer coherent, well-structured, and easy to understand? (0.0 = incoherent, 1.0 = very coherent)

Return a JSON object with:
- 'scores': object with keys 'relevance', 'completeness', 'conciseness', 'accuracy', 'coherence' (each 0.0-1.0)
- 'overall_score': weighted average (float 0.0-1.0)
- 'accepted': boolean indicating if answer quality is acceptable (based on threshold >= 0.65)
- 'reasoning': brief explanation of the scores (2-3 sentences)""",

        "answer_quality_scorer_prompt": answer_quality_scorer_prompt or """Here is the user question:
{question}

Here is the generated answer:
{answer}

Here is the context used to generate the answer:
{context}

Evaluate the answer quality on all 5 criteria. Consider:
- RELEVANCE: Does it directly answer the question?
- COMPLETENESS: Is all necessary information included?
- CONCISENESS: Is it appropriately brief without being too verbose?
- ACCURACY: Is it factually correct based on the context?
- COHERENCE: Is it well-structured and easy to follow?

Return a JSON object with the structure specified in the instructions."""


    }

    return prompts








# Appeler la fonction pour obtenir les prompts
#prompts = get_prompts()

# Afficher un prompt spécifique, par exemple le "router_instructions"
#print(prompts["router_instructions"])