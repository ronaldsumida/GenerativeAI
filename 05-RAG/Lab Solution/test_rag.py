import json
import pytest
from openai import OpenAI
from deepeval import assert_test

from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
)

from deepeval.test_case import LLMTestCase
from tools import retrieve_chunks

client = OpenAI()

SYSTEM_PROMPT = '''
    You are Ask EVE, an assistant that answers questions about electric
    vehicles. Only answer using the context provided below. If the answer
    is not contained in the context, respond with exactly: I don't know.
    '''

with open('golden_dataset.json') as f:
    GOLDEN_SET = json.load(f)

faithfulness = FaithfulnessMetric(threshold=0.7, verbose_mode=False)
answer_relevancy = AnswerRelevancyMetric(threshold=0.7, verbose_mode=False)
contextual_precision = ContextualPrecisionMetric(threshold=0.5, verbose_mode=False)
contextual_recall = ContextualRecallMetric(threshold=0.5, verbose_mode=False)

def generate_answer(question, context):
    context_block = '\n\n'.join(context)

    response = client.chat.completions.create(
        model='gpt-5.4-mini',
        messages=[
            { 'role': 'system', 'content': SYSTEM_PROMPT },
            { 'role': 'user', 'content': f'Context:\n{context_block}\n\nQuestion: {question}' },
        ],
    )

    return response.choices[0].message.content

@pytest.mark.parametrize('item', GOLDEN_SET, ids=[i['question'] for i in GOLDEN_SET])
def test_rag_pipeline(item):
    retrieval_context = retrieve_chunks(item['question'])
    actual_output = generate_answer(item['question'], retrieval_context)

    test_case = LLMTestCase(
        input=item['question'],
        actual_output=actual_output,
        expected_output=item['expected_answer'],
        retrieval_context=retrieval_context,
    )

    assert_test(test_case, [faithfulness, answer_relevancy, contextual_precision, contextual_recall])
