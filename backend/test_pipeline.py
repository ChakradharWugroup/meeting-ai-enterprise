import asyncio
import os
import sys

# Ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ai.summarizer import MeetingSummarizer
from backend.ai.action_items import ActionItemExtractor
from backend.ai.sentiment import SentimentAnalyzer
from backend.reports.pdf import PDFReportGenerator
from backend.reports.docx import DocxReportGenerator
from backend.notifications.email import EmailDispatcher

async def main():
    print("=== ENTERPRISE AI PIPELINE TEST ===\n")
    
    # 1. Define a mock transcript
    meeting_title = "Q3 Marketing Alignment"
    transcript = """
Bob: Alright, let's get started. We need to align on the Q3 marketing budget. Alice, how are we looking?
Alice: We have $50,000 allocated for social media ads. But I think we should shift $10,000 of that to influencer sponsorships.
Bob: That sounds like a great idea. The ROI on influencers has been amazing lately. Alice, can you draft a proposal for the influencer strategy by Friday?
Alice: Sure thing, I will get that done.
Charlie: What about the new website launch? Are we still on track for next month?
Bob: Yes, but we need the final copy from the design team. Charlie, can you follow up with them tomorrow?
Charlie: Will do. I'll make sure they deliver the copy by Wednesday.
Bob: Excellent. I feel very positive about this quarter. Let's reconvene next week.
    """
    
    # 2. Test Ollama AI Integration
    print("[1/3] Calling Local Ollama AI...")
    
    summarizer = MeetingSummarizer(model_name="qwen2:0.5b")
    extractor = ActionItemExtractor(model_name="qwen2:0.5b")
    sentiment_analyzer = SentimentAnalyzer(model_name="qwen2:0.5b")
    
    # Run AI concurrently for speed
    summary_task = summarizer.generate_final_summary(transcript)
    action_items_task = extractor.extract_action_items(transcript)
    sentiment_task = sentiment_analyzer.analyze_sentiment(transcript)
    
    summary, action_items, sentiment = await asyncio.gather(summary_task, action_items_task, sentiment_task)
    
    print(f"\n--- AI Sentiment: {sentiment} ---")
    print(f"\n--- AI Summary ---\n{summary}")
    print(f"\n--- AI Action Items ---\n{action_items}\n")
    
    # 3. Test Report Generation
    print("[2/3] Generating PDF and Word Reports...")
    pdf_gen = PDFReportGenerator(output_dir="test_output")
    docx_gen = DocxReportGenerator(output_dir="test_output")
    
    pdf_path = pdf_gen.generate_report(meeting_title, summary, action_items, transcript)
    docx_path = docx_gen.generate_report(meeting_title, summary, action_items, transcript)
    
    print(f"Success! Reports saved to:\n- {pdf_path}\n- {docx_path}\n")
    
    # 4. Test Email Dispatcher
    print("[3/3] Simulating Email Dispatch...")
    email_sender = EmailDispatcher()
    # This will simulate sending since we don't have real SMTP credentials in .env
    email_sender.send_meeting_report("ceo@company.com", meeting_title, pdf_path)
    
    print("\n=== PIPELINE TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
