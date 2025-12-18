"""
PDF Content Extractor and Summarizer
Supports both simple Python packages and AWS Bedrock models for PDF extraction and summarization.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any


def extract_with_pypdf2(pdf_path: str) -> Dict[str, Any]:
    """
    Extract text from PDF using PyPDF2 (simple Python package).
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary containing extracted content and metadata
    """
    try:
        import PyPDF2
    except ImportError:
        raise ImportError(
            "PyPDF2 is not installed. Install it with: pip install PyPDF2"
        )
    
    content = {
        'text': '',
        'pages': [],
        'metadata': {},
        'num_pages': 0
    }
    
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        content['num_pages'] = len(pdf_reader.pages)
        content['metadata'] = pdf_reader.metadata or {}
        
        for page_num, page in enumerate(pdf_reader.pages, start=1):
            page_text = page.extract_text()
            content['pages'].append({
                'page_number': page_num,
                'text': page_text
            })
            content['text'] += f"\n--- Page {page_num} ---\n{page_text}\n"
    
    return content


def extract_with_pdfplumber(pdf_path: str) -> Dict[str, Any]:
    """
    Extract text from PDF using pdfplumber (better for complex layouts).
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary containing extracted content and metadata
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber is not installed. Install it with: pip install pdfplumber"
        )
    
    content = {
        'text': '',
        'pages': [],
        'metadata': {},
        'num_pages': 0,
        'tables': []
    }
    
    with pdfplumber.open(pdf_path) as pdf:
        content['num_pages'] = len(pdf.pages)
        content['metadata'] = pdf.metadata or {}
        
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ''
            
            # Extract tables if any
            tables = page.extract_tables()
            page_tables = []
            for table in tables:
                page_tables.append(table)
                content['tables'].append({
                    'page': page_num,
                    'table': table
                })
            
            content['pages'].append({
                'page_number': page_num,
                'text': page_text,
                'tables': page_tables
            })
            content['text'] += f"\n--- Page {page_num} ---\n{page_text}\n"
    
    return content


def extract_with_bedrock(pdf_path: str, aws_region: str = 'us-east-1') -> Dict[str, Any]:
    """
    Extract text from PDF using AWS Bedrock (Amazon Textract).
    Requires AWS credentials configured.
    
    Args:
        pdf_path: Path to the PDF file
        aws_region: AWS region for Bedrock service
        
    Returns:
        Dictionary containing extracted content
    """
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
    except ImportError:
        raise ImportError(
            "boto3 is not installed. Install it with: pip install boto3"
        )
    
    try:
        # Initialize Textract client
        textract = boto3.client('textract', region_name=aws_region)
        
        # Read PDF file
        with open(pdf_path, 'rb') as file:
            pdf_bytes = file.read()
        
        # Call Textract
        response = textract.detect_document_text(Document={'Bytes': pdf_bytes})
        
        # Extract text from response
        text_lines = []
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text_lines.append(block['Text'])
        
        content = {
            'text': '\n'.join(text_lines),
            'raw_response': response,
            'num_pages': len([b for b in response.get('Blocks', []) if b.get('BlockType') == 'PAGE']),
            'extraction_method': 'AWS Bedrock (Textract)'
        }
        
        return content
        
    except NoCredentialsError:
        raise Exception(
            "AWS credentials not found. Please configure AWS credentials using:\n"
            "  - AWS CLI: aws configure\n"
            "  - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY\n"
            "  - IAM role (if running on EC2)"
        )
    except ClientError as e:
        raise Exception(f"AWS service error: {str(e)}")


def extract_pdf(
    pdf_path: str,
    method: str = 'pdfplumber',
    aws_region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main function to extract content from PDF.
    
    Args:
        pdf_path: Path to the PDF file
        method: Extraction method ('pypdf2', 'pdfplumber', or 'bedrock')
        aws_region: AWS region (required if method is 'bedrock')
        
    Returns:
        Dictionary containing extracted content
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if not pdf_path.suffix.lower() == '.pdf':
        raise ValueError(f"File is not a PDF: {pdf_path}")
    
    print(f"Extracting content from: {pdf_path}")
    print(f"Method: {method}")
    
    if method == 'pypdf2':
        return extract_with_pypdf2(str(pdf_path))
    elif method == 'pdfplumber':
        return extract_with_pdfplumber(str(pdf_path))
    elif method == 'bedrock':
        if not aws_region:
            aws_region = 'us-east-1'
        return extract_with_bedrock(str(pdf_path), aws_region)
    else:
        raise ValueError(
            f"Unknown method: {method}. "
            "Supported methods: 'pypdf2', 'pdfplumber', 'bedrock'"
        )


def summarize_with_bedrock(
    text: str,
    aws_region: str = 'us-east-1',
    model_id: str = 'anthropic.claude-3-sonnet-20240229-v1:0',
    summary_type: str = 'architecture'
) -> Dict[str, Any]:
    """
    Summarize text using AWS Bedrock (Claude models).
    Optimized for architecture diagram generation.
    
    Args:
        text: Text content to summarize
        aws_region: AWS region for Bedrock service
        model_id: Bedrock model ID to use
        summary_type: Type of summary ('architecture', 'general', 'detailed')
        
    Returns:
        Dictionary containing summary and metadata
    """
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
    except ImportError:
        raise ImportError(
            "boto3 is not installed. Install it with: pip install boto3"
        )
    
    # Create architecture-focused prompt
    architecture_prompt = """You are an expert system architect. Analyze the following document and create a comprehensive summary focused on architecture and technical components that would be useful for generating an architecture diagram.

Please extract and summarize:
1. **System Overview**: Main purpose, use case, and high-level architecture
2. **Core Components**: Key services, applications, databases, APIs, and infrastructure components
3. **Data Flow**: How data moves through the system, including inputs, processing steps, and outputs
4. **Technology Stack**: AWS services, frameworks, tools, and technologies used
5. **Integration Points**: External systems, APIs, and third-party services
6. **Deployment Architecture**: Deployment strategies, environments, and infrastructure patterns
7. **Key Workflows**: Main processes, pipelines, and automated workflows
8. **Storage & Databases**: Data storage solutions, databases, and data management
9. **Monitoring & Observability**: Logging, monitoring, and alerting components
10. **Security & Access**: Authentication, authorization, and security mechanisms

Format the summary in a clear, structured way that would help someone create an accurate architecture diagram. Focus on technical components, their relationships, and data flows.

Document content:
{text}

Please provide a comprehensive architecture-focused summary:"""

    general_prompt = """Please provide a comprehensive summary of the following document. Focus on key points, main topics, and important information.

Document content:
{text}

Summary:"""

    detailed_prompt = """Please provide a detailed summary of the following document. Include all important sections, key points, technical details, and relevant information.

Document content:
{text}

Detailed Summary:"""

    # Select prompt based on summary type
    if summary_type == 'architecture':
        prompt_template = architecture_prompt
    elif summary_type == 'detailed':
        prompt_template = detailed_prompt
    else:
        prompt_template = general_prompt
    
    prompt = prompt_template.format(text=text)
    
    # Truncate text if too long (Bedrock has token limits)
    # Claude 3.5 Sonnet supports up to 200k tokens, but we'll be conservative
    max_chars = 180000  # Leave room for prompt and response
    if len(text) > max_chars:
        print(f"Warning: Text is very long ({len(text)} chars). Truncating to {max_chars} chars for summarization.")
        text = text[:max_chars]
        prompt = prompt_template.format(text=text)
    
    try:
        # Initialize Bedrock runtime client
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=aws_region)
        
        # Prepare the request body for Claude
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Invoke the model
        print(f"Invoking Bedrock model: {model_id}")
        print("This may take a moment...")
        
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read())
        
        # Extract the summary text
        summary_text = ""
        if 'content' in response_body:
            for content_block in response_body['content']:
                if content_block.get('type') == 'text':
                    summary_text += content_block.get('text', '')
        
        result = {
            'summary': summary_text,
            'model_id': model_id,
            'summary_type': summary_type,
            'input_length': len(text),
            'summary_length': len(summary_text),
            'usage': response_body.get('usage', {})
        }
        
        return result
        
    except NoCredentialsError:
        raise Exception(
            "AWS credentials not found. Please configure AWS credentials using:\n"
            "  - AWS CLI: aws configure\n"
            "  - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY\n"
            "  - IAM role (if running on EC2)"
        )
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        
        if error_code == 'ValidationException':
            # Try alternative model IDs
            alternative_models = [
                'anthropic.claude-3-sonnet-20240229-v1:0',
                'anthropic.claude-3-haiku-20240307-v1:0',
                'anthropic.claude-3-sonnet-20240229-v1:0:200k',
                'anthropic.claude-3-sonnet-20240229-v1:0:28k'
            ]
            raise Exception(
                f"Model {model_id} may not be available in region {aws_region}.\n"
                f"Error: {error_message}\n"
                f"Try using one of these models: {', '.join(alternative_models)}\n"
                f"Use --bedrock-model-id to specify a different model."
            )
        else:
            raise Exception(f"AWS Bedrock error ({error_code}): {error_message}")


def save_extracted_content(content: Dict[str, Any], output_path: Optional[str] = None):
    """
    Save extracted content to a text file.
    
    Args:
        content: Extracted content dictionary
        output_path: Path to save the output file (optional)
    """
    if output_path is None:
        output_path = 'extracted_content.txt'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PDF CONTENT EXTRACTION RESULTS\n")
        f.write("=" * 80 + "\n\n")
        
        if 'num_pages' in content:
            f.write(f"Total Pages: {content['num_pages']}\n\n")
        
        if 'metadata' in content and content['metadata']:
            f.write("Metadata:\n")
            for key, value in content['metadata'].items():
                f.write(f"  {key}: {value}\n")
            f.write("\n")
        
        f.write("=" * 80 + "\n")
        f.write("EXTRACTED TEXT\n")
        f.write("=" * 80 + "\n\n")
        f.write(content.get('text', ''))
        
        if 'tables' in content and content['tables']:
            f.write("\n\n" + "=" * 80 + "\n")
            f.write("EXTRACTED TABLES\n")
            f.write("=" * 80 + "\n\n")
            for idx, table_info in enumerate(content['tables'], 1):
                f.write(f"Table {idx} (Page {table_info['page']}):\n")
                for row in table_info['table']:
                    f.write("  " + " | ".join(str(cell) if cell else "" for cell in row) + "\n")
                f.write("\n")
    
    print(f"\nExtracted content saved to: {output_path}")


def save_summary(summary: Dict[str, Any], output_path: Optional[str] = None):
    """
    Save summary to a text file.
    
    Args:
        summary: Summary dictionary
        output_path: Path to save the output file (optional)
    """
    if output_path is None:
        output_path = 'summary.txt'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PDF CONTENT SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Summary Type: {summary.get('summary_type', 'general').title()}\n")
        f.write(f"Model: {summary.get('model_id', 'N/A')}\n")
        f.write(f"Input Length: {summary.get('input_length', 0):,} characters\n")
        f.write(f"Summary Length: {summary.get('summary_length', 0):,} characters\n")
        
        if 'usage' in summary and summary['usage']:
            f.write(f"\nToken Usage:\n")
            f.write(f"  Input Tokens: {summary['usage'].get('input_tokens', 'N/A')}\n")
            f.write(f"  Output Tokens: {summary['usage'].get('output_tokens', 'N/A')}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("SUMMARY CONTENT\n")
        f.write("=" * 80 + "\n\n")
        f.write(summary.get('summary', ''))
    
    print(f"\nSummary saved to: {output_path}")


def main():
    """Command-line interface for PDF extraction and summarization."""
    parser = argparse.ArgumentParser(
        description='Extract and summarize content from PDF documents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract using pdfplumber (default, recommended)
  python pdf_extractor.py document.pdf
  
  # Extract and summarize for architecture diagram
  python pdf_extractor.py document.pdf --summarize --summary-type architecture
  
  # Extract using PyPDF2
  python pdf_extractor.py document.pdf --method pypdf2
  
  # Extract using AWS Bedrock and summarize
  python pdf_extractor.py document.pdf --method bedrock --summarize --aws-region us-east-1
  
  # Save to specific output file
  python pdf_extractor.py document.pdf --output extracted.txt
  
  # Summarize with custom Bedrock model
  python pdf_extractor.py document.pdf --summarize --bedrock-model-id anthropic.claude-3-sonnet-20240229-v1:0
        """
    )
    
    parser.add_argument(
        'pdf_path',
        type=str,
        help='Path to the PDF file'
    )
    
    parser.add_argument(
        '--method',
        type=str,
        choices=['pypdf2', 'pdfplumber', 'bedrock'],
        default='pdfplumber',
        help='Extraction method (default: pdfplumber)'
    )
    
    parser.add_argument(
        '--aws-region',
        type=str,
        default=None,
        help='AWS region for Bedrock (required if method is bedrock)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file path (default: extracted_content.txt)'
    )
    
    parser.add_argument(
        '--print-text',
        action='store_true',
        help='Print extracted text to console'
    )
    
    parser.add_argument(
        '--summarize',
        action='store_true',
        help='Summarize the extracted content using AWS Bedrock'
    )
    
    parser.add_argument(
        '--summary-type',
        type=str,
        choices=['architecture', 'general', 'detailed'],
        default='architecture',
        help='Type of summary to generate (default: architecture)'
    )
    
    parser.add_argument(
        '--bedrock-model-id',
        type=str,
        default='anthropic.claude-3-5-sonnet-20241022-v2:0',
        help='Bedrock model ID for summarization (default: anthropic.claude-3-5-sonnet-20241022-v2:0)'
    )
    
    parser.add_argument(
        '--summary-output',
        type=str,
        default=None,
        help='Output file path for summary (default: summary.txt)'
    )
    
    args = parser.parse_args()
    
    try:
        # Extract content
        content = extract_pdf(
            pdf_path=args.pdf_path,
            method=args.method,
            aws_region=args.aws_region
        )
        
        # Print summary
        print(f"\n✓ Extraction completed successfully!")
        print(f"  Pages extracted: {content.get('num_pages', 'N/A')}")
        print(f"  Text length: {len(content.get('text', ''))} characters")
        
        if 'tables' in content:
            print(f"  Tables found: {len(content['tables'])}")
        
        # Print text if requested
        if args.print_text:
            print("\n" + "=" * 80)
            print("EXTRACTED TEXT:")
            print("=" * 80)
            print(content.get('text', ''))
        
        # Save to file
        save_extracted_content(content, args.output)
        
        # Summarize if requested
        if args.summarize:
            print("\n" + "=" * 80)
            print("SUMMARIZING CONTENT...")
            print("=" * 80)
            
            if not args.aws_region:
                args.aws_region = 'us-east-1'
            
            try:
                summary = summarize_with_bedrock(
                    text=content.get('text', ''),
                    aws_region=args.aws_region,
                    model_id=args.bedrock_model_id,
                    summary_type=args.summary_type
                )
                
                print(f"\n✓ Summarization completed successfully!")
                print(f"  Summary type: {summary.get('summary_type', 'N/A')}")
                print(f"  Model used: {summary.get('model_id', 'N/A')}")
                print(f"  Input length: {summary.get('input_length', 0):,} characters")
                print(f"  Summary length: {summary.get('summary_length', 0):,} characters")
                
                if 'usage' in summary and summary['usage']:
                    print(f"  Input tokens: {summary['usage'].get('input_tokens', 'N/A')}")
                    print(f"  Output tokens: {summary['usage'].get('output_tokens', 'N/A')}")
                
                # Print summary if requested
                if args.print_text:
                    print("\n" + "=" * 80)
                    print("SUMMARY:")
                    print("=" * 80)
                    print(summary.get('summary', ''))
                
                # Save summary to file
                save_summary(summary, args.summary_output)
                
            except Exception as e:
                print(f"Error during summarization: {str(e)}", file=sys.stderr)
                print("\nNote: Summarization failed, but extraction was successful.")
                print("Make sure AWS credentials are configured and Bedrock access is enabled.")
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

