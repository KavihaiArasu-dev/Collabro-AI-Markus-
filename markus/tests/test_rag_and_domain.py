"""
Unit tests for Clean Architecture Domain, State Machine, and RAG Knowledge Base.
"""

import unittest
from domain.entities import ChatMessage, MessageRole, DocumentChunk
from domain.state_machine import StateMachine, ConversationState, InvalidTransitionError
from rag.chunker import DocumentChunker
from rag.vector_store import VectorStore
from rag.retriever import RAGRetriever


class TestDomainAndRAG(unittest.TestCase):

    def test_state_machine_valid_lifecycle(self):
        sm = StateMachine()
        self.assertEqual(sm.current_state, ConversationState.IDLE)

        # Wake-up: IDLE -> ACTIVATED -> LISTENING -> THINKING -> SPEAKING -> IDLE
        sm.transition_to(ConversationState.ACTIVATED)
        self.assertEqual(sm.current_state, ConversationState.ACTIVATED)

        sm.transition_to(ConversationState.LISTENING)
        self.assertEqual(sm.current_state, ConversationState.LISTENING)

        sm.transition_to(ConversationState.THINKING)
        self.assertEqual(sm.current_state, ConversationState.THINKING)

        sm.transition_to(ConversationState.SPEAKING)
        self.assertEqual(sm.current_state, ConversationState.SPEAKING)

        sm.transition_to(ConversationState.IDLE)
        self.assertEqual(sm.current_state, ConversationState.IDLE)

    def test_state_machine_invalid_transition(self):
        sm = StateMachine()
        # Direct transition from IDLE to THINKING is illegal
        with self.assertRaises(InvalidTransitionError):
            sm.transition_to(ConversationState.THINKING)

    def test_rag_chunking_and_retrieval(self):
        chunker = DocumentChunker(chunk_size=120, chunk_overlap=30)
        sample_doc = (
            "Markus AI is a personal development assistant built with Clean Architecture.\n\n"
            "It incorporates RAG (Retrieval-Augmented Generation) to answer questions from local files.\n\n"
            "The system includes real-time face tracking and emotion estimation using OpenCV."
        )

        chunks = chunker.chunk_text(sample_doc, "architecture_notes.md")
        self.assertTrue(len(chunks) >= 2)

        # Test VectorStore indexing and search
        vs = VectorStore(storage_path="./data/test_vector_store.json")
        vs.clear()
        vs.add_chunks(chunks)

        retriever = RAGRetriever()
        results = vs.similarity_search("clean architecture RAG", top_k=2)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0].chunk.doc_name, "architecture_notes.md")


if __name__ == "__main__":
    unittest.main()
