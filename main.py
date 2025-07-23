import json
import re
import os
from typing import List, Dict, Any
import fitz  # PyMuPDF (imported as fitz)
from PIL import Image
import io

class PDFContentAnalyzer:
    """
    A comprehensive PDF content analyzer that extracts text, images, and generates
    structured question data for educational content analysis.
    """
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.output_dir = "extracted_content"
        self.images_dir = os.path.join(self.output_dir, "images")
        self.ensure_directories()
    
    def ensure_directories(self):
        """Create necessary directories for output."""
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
    
    def extract_text_from_page(self, page_num: int) -> str:
        """Extract text content from a specific page."""
        page = self.doc[page_num]
        return page.get_text()
    
    def extract_images_from_page(self, page_num: int) -> List[str]:
        """Extract images from a specific page and save them."""
        page = self.doc[page_num]
        image_list = page.get_images()
        image_paths = []
        
        for img_index, img in enumerate(image_list):
            # Get image data
            xref = img[0]
            pix = fitz.Pixmap(self.doc, xref)
            
            # Convert to PIL Image if needed
            if pix.n - pix.alpha < 4:  # GRAY or RGB
                img_data = pix.tobytes("png")
                image_filename = f"page{page_num + 1}_image{img_index + 1}.png"
                image_path = os.path.join(self.images_dir, image_filename)
                
                with open(image_path, "wb") as img_file:
                    img_file.write(img_data)
                
                image_paths.append(image_path)
            
            pix = None  # Free memory
        
        return image_paths
    
    def parse_question_from_text(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        """Parse questions from extracted text."""
        questions = []
        
        # Split text into lines and process
        lines = text.strip().split('\n')
        current_question = None
        question_text = ""
        options = []
        answer = ""
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
            
            # Check if line starts with a number (indicating a new question)
            if re.match(r'^\d+\.', line):
                # Save previous question if exists
                if current_question is not None and question_text:
                    questions.append({
                        "question_number": current_question,
                        "question": question_text.strip(),
                        "options": options.copy(),
                        "answer": answer,
                        "page": page_num + 1,
                        "images": f"page{page_num + 1}_question{current_question}.png",
                        "option_images": [f"page{page_num + 1}_option{j}.png" for j in range(len(options))]
                    })
                
                # Start new question
                current_question = int(line.split('.')[0])
                question_text = line[line.find('.') + 1:].strip()
                options = []
                answer = ""
            
            # Check for options [A], [B], [C], [D]
            elif re.match(r'^\[([ABCD])\]', line):
                option_match = re.match(r'^\[([ABCD])\]\s*(.*)', line)
                if option_match:
                    option_letter = option_match.group(1)
                    option_text = option_match.group(2).strip()
                    options.append(f"[{option_letter}] {option_text}")
            
            # Check for answer
            elif line.startswith('Ans'):
                answer_match = re.search(r'\[([ABCD])\]', line)
                if answer_match:
                    answer = answer_match.group(1)
            
            # Otherwise, it's part of the question text
            else:
                if current_question is not None:
                    question_text += " " + line
            
            i += 1
        
        # Don't forget the last question
        if current_question is not None and question_text:
            questions.append({
                "question_number": current_question,
                "question": question_text.strip(),
                "options": options.copy(),
                "answer": answer,
                "page": page_num + 1,
                "images": f"page{page_num + 1}_question{current_question}.png",
                "option_images": [f"page{page_num + 1}_option{j}.png" for j in range(len(options))]
            })
        
        return questions
    
    def extract_all_content(self) -> Dict[str, Any]:
        """Extract all content from the PDF."""
        all_content = {
            "pdf_info": {
                "filename": os.path.basename(self.pdf_path),
                "total_pages": len(self.doc),
                "extraction_summary": {}
            },
            "pages": [],
            "questions": []
        }
        
        total_images = 0
        total_questions = 0
        
        for page_num in range(len(self.doc)):
            print(f"Processing page {page_num + 1}...")
            
            # Extract text
            page_text = self.extract_text_from_page(page_num)
            
            # Extract images
            page_images = self.extract_images_from_page(page_num)
            total_images += len(page_images)
            
            # Parse questions from text
            page_questions = self.parse_question_from_text(page_text, page_num)
            total_questions += len(page_questions)
            
            # Store page content
            page_content = {
                "page_number": page_num + 1,
                "text": page_text,
                "images": page_images,
                "questions_found": len(page_questions)
            }
            
            all_content["pages"].append(page_content)
            all_content["questions"].extend(page_questions)
        
        # Update summary
        all_content["pdf_info"]["extraction_summary"] = {
            "total_images_extracted": total_images,
            "total_questions_found": total_questions,
            "pages_processed": len(self.doc)
        }
        
        return all_content
    
    def generate_structured_json(self) -> List[Dict[str, Any]]:
        """Generate the structured JSON as specified in the assignment."""
        content = self.extract_all_content()
        structured_questions = []
        
        for question in content["questions"]:
            # Create the structure as requested in the assignment
            structured_question = {
                "question_number": question.get("question_number"),
                "question": question.get("question", ""),
                "options": question.get("options", []),
                "answer": question.get("answer", ""),
                "page": question.get("page", 1),
                "images": question.get("images", ""),
                "option_images": question.get("option_images", [])
            }
            structured_questions.append(structured_question)
        
        return structured_questions
    
    def save_results(self):
        """Save all results to files."""
        # Generate structured content
        structured_content = self.generate_structured_json()
        
        # Save structured JSON (as requested in assignment)
        structured_json_path = os.path.join(self.output_dir, "structured_questions.json")
        with open(structured_json_path, 'w', encoding='utf-8') as f:
            json.dump(structured_content, f, indent=2, ensure_ascii=False)
        
        # Also save complete extraction data
        complete_content = self.extract_all_content()
        complete_json_path = os.path.join(self.output_dir, "complete_extraction.json")
        with open(complete_json_path, 'w', encoding='utf-8') as f:
            json.dump(complete_content, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Extraction completed successfully!")
        print(f"📁 Output directory: {self.output_dir}")
        print(f"📄 Structured questions: {structured_json_path}")
        print(f"📄 Complete extraction: {complete_json_path}")
        print(f"🖼️  Images saved in: {self.images_dir}")
        print(f"📊 Total questions found: {len(structured_content)}")
        
        return structured_content
    
    def close(self):
        """Close the PDF document."""
        self.doc.close()


def main():
    """Main function to run the PDF content analyzer."""
    # Path to the PDF file (update this path as needed)
    pdf_path = "IMO class 1 Maths Olympiad Sample Paper 1 for the year 2024-25.pdf"
    
    try:
        # Create analyzer instance
        analyzer = PDFContentAnalyzer(pdf_path)
        
        print("🚀 Starting PDF content analysis...")
        print(f"📖 Processing: {pdf_path}")
        
        # Extract and save all content
        results = analyzer.save_results()
        
        # Display sample results
        print("\n📋 Sample extracted questions:")
        for i, question in enumerate(results[:3]):  # Show first 3 questions
            print(f"\nQuestion {question['question_number']}:")
            print(f"Text: {question['question'][:100]}...")
            print(f"Options: {len(question['options'])} found")
            print(f"Answer: {question['answer']}")
            print(f"Page: {question['page']}")
        
        # Close the document
        analyzer.close()
        
    except FileNotFoundError:
        print(f"❌ Error: PDF file '{pdf_path}' not found.")
        print("Please make sure the PDF file is in the same directory as this script.")
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")


if __name__ == "__main__":
    main()


# Additional utility functions for advanced analysis

class QuestionAnalyzer:
    """Additional utility class for analyzing extracted questions."""
    
    @staticmethod
    def categorize_questions(questions: List[Dict]) -> Dict[str, List]:
        """Categorize questions by type/section."""
        categories = {
            "logical_reasoning": [],
            "mathematics": [],
            "achiever_section": []
        }
        
        for question in questions:
            q_num = question.get("question_number", 0)
            if 1 <= q_num <= 5:
                categories["logical_reasoning"].append(question)
            elif 6 <= q_num <= 30:
                categories["mathematics"].append(question)
            elif q_num >= 31:
                categories["achiever_section"].append(question)
        
        return categories
    
    @staticmethod
    def generate_statistics(questions: List[Dict]) -> Dict[str, Any]:
        """Generate statistics about the extracted questions."""
        categories = QuestionAnalyzer.categorize_questions(questions)
        
        stats = {
            "total_questions": len(questions),
            "by_category": {
                "logical_reasoning": len(categories["logical_reasoning"]),
                "mathematics": len(categories["mathematics"]),
                "achiever_section": len(categories["achiever_section"])
            },
            "answer_distribution": {},
            "questions_with_images": 0
        }
        
        # Count answer distribution
        for question in questions:
            answer = question.get("answer", "")
            stats["answer_distribution"][answer] = stats["answer_distribution"].get(answer, 0) + 1
        
        # Count questions with images
        stats["questions_with_images"] = sum(1 for q in questions if q.get("images"))
        
        return stats


# Example usage with the provided sample file
def analyze_sample_file():
    """Analyze the provided sample file and generate detailed report."""
    pdf_path = "IMO class 1 Maths Olympiad Sample Paper 1 for the year 2024-25.pdf"
    
    try:
        analyzer = PDFContentAnalyzer(pdf_path)
        results = analyzer.save_results()
        
        # Generate additional analysis
        stats = QuestionAnalyzer.generate_statistics(results)
        categories = QuestionAnalyzer.categorize_questions(results)
        
        print("\n📊 DETAILED ANALYSIS REPORT:")
        print("=" * 50)
        print(f"Total Questions Extracted: {stats['total_questions']}")
        print(f"Logical Reasoning: {stats['by_category']['logical_reasoning']}")
        print(f"Mathematics: {stats['by_category']['mathematics']}")
        print(f"Achiever Section: {stats['by_category']['achiever_section']}")
        print(f"Questions with Images: {stats['questions_with_images']}")
        
        print("\nAnswer Distribution:")
        for answer, count in stats["answer_distribution"].items():
            print(f"  {answer}: {count} questions")
        
        analyzer.close()
        
    except Exception as e:
        print(f"Error in analysis: {str(e)}")


if __name__ == "__main__":
    # Run the main analysis
    main()
    
    # Run additional detailed analysis
    print("\n" + "="*60)
    analyze_sample_file()