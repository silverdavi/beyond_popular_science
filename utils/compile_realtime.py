#!/usr/bin/env python3
"""
Real-time LaTeX compilation with progress tracking and live updates.
"""

import subprocess
import time
import threading
import os
import re
import sys
import argparse
from datetime import datetime, timedelta

class RealTimeCompiler:
    def __init__(self, tex_file='main.tex'):
        self.tex_file = tex_file
        self.base_name = os.path.splitext(tex_file)[0]
        self.start_time = None
        self.current_chapter = 0
        self.total_chapters = 0
        self.phase = "Initializing"
        self.log_lines = []
        self.process = None
        self.monitoring = True
        
    def count_chapters(self):
        """Count total chapters by looking for chapterwithsummaryfromfile statements."""
        try:
            with open(self.tex_file, 'r') as f:
                content = f.read()
            # Count only non-commented chapterwithsummaryfromfile commands
            chapter_count = 0
            for line in content.split('\n'):
                # Skip commented lines
                stripped_line = line.strip()
                if not stripped_line.startswith('%') and '\\chapterwithsummaryfromfile' in line:
                    chapter_count += 1
            return chapter_count
        except:
            return 50  # fallback estimate
    
    def extract_chapter_info(self, line):
        """Extract chapter information from log line."""
        # Look for chapter files being processed
        if '/' in line and any(ext in line for ext in ['title.tex', 'summary.tex', 'main.tex']):
            # Extract chapter number from path like "./01_BanachTarskiParadox/title.tex"
            match = re.search(r'(\d+)_([^/]+)/', line)
            if match:
                chapter_num = int(match.group(1))
                chapter_name = match.group(2)
                return chapter_num, chapter_name
        return None, None
    
    def clean_build_artifacts(self):
        """Clean all build artifacts from previous compilations."""
        print("[clean] Cleaning build artifacts...")
        
        # LaTeX build files
        latex_extensions = [
            'aux', 'toc', 'log', 'out', 'fdb_latexmk', 'fls',
            'bbl', 'blg', 'idx', 'ind', 'ilg', 'lof', 'lot', 'nav', 'snm', 'vrb'
        ]
        
        cleaned_count = 0
        
        # Clean document artifacts
        for ext in latex_extensions:
            file_path = f'{self.base_name}.{ext}'
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    cleaned_count += 1
                except Exception as e:
                    print(f"  [warn]  Could not remove {file_path}: {e}")
        
        # Clean compilation log files
        for log_file in ['compile_pass1.log', 'compile_pass2.log']:
            if os.path.exists(log_file):
                try:
                    os.remove(log_file)
                    cleaned_count += 1
                except Exception as e:
                    print(f"  [warn]  Could not remove {log_file}: {e}")
        
        # Clean any LaTeX auxiliary files in subdirectories
        for root, dirs, files in os.walk('.'):
            # CRITICAL: Skip .git directory to avoid corrupting git repository
            if '.git' in root:
                continue
            
            for file in files:
                if any(file.endswith(f'.{ext}') for ext in latex_extensions):
                    file_path = os.path.join(root, file)
                    # Skip main.pdf and other important PDFs
                    if not file.endswith('.pdf') or file.startswith('main.'):
                        try:
                            os.remove(file_path)
                            cleaned_count += 1
                        except Exception as e:
                            pass  # Silent fail for subdirectory cleanup
        
        print(f"  [ok] Cleaned {cleaned_count} build artifacts")
    
    def format_time(self, seconds):
        """Format seconds into readable time."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def estimate_remaining_time(self, elapsed, progress):
        """Estimate remaining compilation time."""
        if progress > 0.05:  # Only estimate after 5% progress
            total_estimated = elapsed / progress
            remaining = total_estimated - elapsed
            return max(0, remaining)
        return None
    
    def print_progress(self, chapter_num, chapter_name, elapsed):
        """Print current progress with time estimates."""
        if self.total_chapters > 0:
            progress = chapter_num / self.total_chapters
            bar_length = 40
            filled_length = int(bar_length * progress)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            
            remaining_time = self.estimate_remaining_time(elapsed, progress)
            remaining_str = f" | ETA: {self.format_time(remaining_time)}" if remaining_time else ""
            
            print(f"\r[..] [{bar}] {progress*100:.1f}% | Ch.{chapter_num:02d}: {chapter_name[:20]:<20} | {self.format_time(elapsed)}{remaining_str}", end="", flush=True)
    
    def monitor_log_file(self, log_file):
        """Monitor log file in real-time."""
        last_pos = 0
        mystery_strings = []
        
        while self.monitoring:
            try:
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(last_pos)
                        new_lines = f.readlines()
                        last_pos = f.tell()
                        
                        for line in new_lines:
                            line = line.strip()
                            if line:
                                self.log_lines.append(line)
                                
                                # Check for mystery strings
                                if re.match(r'^\d+show[A-Za-z]+$', line):
                                    mystery_strings.append(line)
                                    print(f"\n[debug] Mystery string detected: '{line}'")
                                
                                # Extract chapter info
                                chapter_num, chapter_name = self.extract_chapter_info(line)
                                if chapter_num and chapter_name:
                                    self.current_chapter = max(self.current_chapter, chapter_num)
                                    elapsed = time.time() - self.start_time
                                    self.print_progress(chapter_num, chapter_name, elapsed)
                                
                                # Check for completion
                                if "Output written on" in line:
                                    self.phase = "Completed"
                                    self.pdf_generated = True
                                    match = re.search(r'(\d+) pages.*?(\d+) bytes', line)
                                    if match:
                                        pages, size_bytes = match.groups()
                                        size_mb = int(size_bytes) / (1024*1024)
                                        print(f"\n[ok] PDF generated: {pages} pages, {size_mb:.1f}MB")
                                
                                # Check for errors (but ignore normal LaTeX loading messages)
                                if any(err in line.lower() for err in ['error', 'emergency stop', '! ']):
                                    # Ignore false positives: file paths, loading messages, and warnings
                                    if ('warning' not in line.lower() and 
                                        not line.strip().startswith('(') and  # File loading paths
                                        '.code.tex' not in line and           # LaTeX code files
                                        '.sty' not in line and                # Style files
                                        'errorbars.cod' not in line):          # Specific pgfplots false positive
                                        print(f"\n[error] Error detected: {line}")
                
                time.sleep(0.1)  # Check every 100ms
            except Exception as e:
                time.sleep(0.5)
        
        return mystery_strings
    
    def compile_pass(self, pass_num, log_file):
        """Compile a single pass with monitoring."""
        print(f"\n[info] Pass {pass_num}: {'Building document structure' if pass_num == 1 else 'Finalizing cross-references'}")
        
        self.start_time = time.time()
        self.current_chapter = 0
        self.monitoring = True
        self.pdf_generated = False
        
        # Start log monitoring in background
        log_thread = threading.Thread(target=self.monitor_log_file, args=(log_file,))
        log_thread.daemon = True
        log_thread.start()
        
        # Start compilation
        cmd = ['lualatex', '-interaction=nonstopmode', '--synctex=1', self.tex_file]
        self.process = subprocess.Popen(
            cmd, 
            stdout=open(log_file, 'w'), 
            stderr=subprocess.STDOUT,
            cwd='.'
        )
        
        # Wait for completion
        return_code = self.process.wait()
        self.monitoring = False
        
        elapsed = time.time() - self.start_time
        
        # Success is determined by PDF generation, not exit code (LaTeX can have warnings)
        success = self.pdf_generated or os.path.exists(f'{self.base_name}.pdf')
        
        if success:
            print(f"\n[ok] Pass {pass_num} completed in {self.format_time(elapsed)}")
        else:
            print(f"\n[error] Pass {pass_num} failed after {self.format_time(elapsed)}")
            
        return success
    
    def compile_document(self):
        """Compile the document with real-time progress."""
        print("[start] REAL-TIME LATEX COMPILATION")
        print("=" * 50)
        
        # Count chapters
        self.total_chapters = self.count_chapters()
        print(f"[info] Detected {self.total_chapters} chapters")
        
        # Clean old files
        self.clean_build_artifacts()
        
        overall_start = time.time()
        
        # First pass
        success1 = self.compile_pass(1, 'compile_pass1.log')
        if not success1:
            print("[error] First pass failed, aborting.")
            return False
        
        # Second pass  
        success2 = self.compile_pass(2, 'compile_pass2.log')
        
        total_time = time.time() - overall_start
        
        print(f"\n[done] COMPILATION COMPLETE")
        print(f"[time]  Total time: {self.format_time(total_time)}")
        
        # Check final results
        pdf_file = f'{self.base_name}.pdf'
        if os.path.exists(pdf_file):
            pdf_size = os.path.getsize(pdf_file) / (1024*1024)
            print(f"[file] PDF: {pdf_size:.1f}MB")
        
        toc_file = f'{self.base_name}.toc'
        if os.path.exists(toc_file):
            toc_size = os.path.getsize(toc_file)
            if toc_size > 0:
                print(f"[info] ToC: {toc_size} bytes")
            else:
                print("[warn]  ToC is empty (0 bytes) - check for issues!")
        
        # Generate page structure table if compilation succeeded
        if success1 and success2:
            self.generate_page_structure_table()
            # Also concatenate book content
            self.concatenate_book_content()
            # Generate simple title+summary concatenation
            self.concatenate_titles_summaries()
        
        return success1 and success2
    def generate_page_structure_table(self):
        """Generate detailed page structure CSV table."""
        pdf_file = f'{self.base_name}.pdf'
        
        if not os.path.exists(pdf_file):
            print(f"[warn]  PDF file not found: {pdf_file} - skipping page structure table")
            return
        
        try:
            # Use the dedicated page table generation script
            result = subprocess.run([
                sys.executable, 'utils/generate_page_table.py', pdf_file, self.base_name
            ], capture_output=True, text=True, cwd='.')
            
            if result.returncode == 0:
                # Print the output from the script
                for line in result.stdout.split('\n'):
                    if line.strip():
                        print(f"  {line}")
            else:
                print(f"[error] Page structure table generation failed: {result.stderr}")
                
        except Exception as e:
            print(f"[error] Could not run page structure analysis: {e}")
    
    def concatenate_book_content(self):
        """Concatenate all book content into a single text/tex file."""
        output_file = f'{self.base_name}_concatenated.tex'
        
        print(f"\n[info] CONCATENATING BOOK CONTENT")
        print("=" * 50)
        
        try:
            with open(self.tex_file, 'r', encoding='utf-8') as main_file:
                main_content = main_file.read()
            
            # Extract list of chapter directories
            chapter_dirs = []
            for line in main_content.split('\n'):
                stripped = line.strip()
                if not stripped.startswith('%') and '\\inputstory{' in line:
                    match = re.search(r'\\inputstory\{([^}]+)\}', line)
                    if match:
                        chapter_dirs.append(match.group(1))
            
            with open(output_file, 'w', encoding='utf-8') as out:
                # Write header
                out.write(f"% Concatenated book content from {self.tex_file}\n")
                out.write(f"% Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                out.write(f"% Total chapters: {len(chapter_dirs)}\n\n")
                out.write("="*80 + "\n\n")
                
                # Concatenate each chapter
                for i, chapter_dir in enumerate(chapter_dirs, 1):
                    out.write(f"\n{'='*80}\n")
                    out.write(f"CHAPTER {i}: {chapter_dir}\n")
                    out.write(f"{'='*80}\n\n")
                    
                    # Read each component file
                    for component in ['title.tex', 'summary.tex', 'topicmap.tex', 
                                    'quote.tex', 'historical.tex', 'main.tex', 'technical.tex']:
                        file_path = os.path.join(chapter_dir, component)
                        if os.path.exists(file_path):
                            out.write(f"\n--- {component.upper()} ---\n\n")
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                out.write(f.read())
                            out.write("\n")
                
                # Add biographical reference if it exists
                if os.path.exists('oneline_bios_content.tex'):
                    out.write(f"\n\n{'='*80}\n")
                    out.write(f"BIOGRAPHICAL REFERENCE\n")
                    out.write(f"{'='*80}\n\n")
                    with open('oneline_bios_content.tex', 'r', encoding='utf-8') as f:
                        out.write(f.read())
            
            file_size = os.path.getsize(output_file) / (1024*1024)
            print(f"[ok] Concatenated book saved: {output_file}")
            print(f"   Size: {file_size:.2f}MB, {len(chapter_dirs)} chapters")
            return True
            
        except Exception as e:
            print(f"[error] Concatenation failed: {e}")
            return False
    
    def concatenate_titles_summaries(self):
        """Concatenate just title.tex + summary.tex for all chapters."""
        output_file = 'all_titles_summaries.tex'
        
        print(f"\n[info] GENERATING TITLES + SUMMARIES")
        print("=" * 50)
        
        try:
            with open(self.tex_file, 'r', encoding='utf-8') as main_file:
                main_content = main_file.read()
            
            # Extract list of chapter directories
            chapter_dirs = []
            for line in main_content.split('\n'):
                stripped = line.strip()
                if not stripped.startswith('%') and '\\inputstory{' in line:
                    match = re.search(r'\\inputstory\{([^}]+)\}', line)
                    if match:
                        chapter_dirs.append(match.group(1))
            
            with open(output_file, 'w', encoding='utf-8') as out:
                # Write header
                out.write(f"% All Titles + Summaries from {self.tex_file}\n")
                out.write(f"% Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                out.write(f"% Total chapters: {len(chapter_dirs)}\n\n")
                out.write("="*80 + "\n\n")
                
                # Concatenate each chapter's title and summary
                for i, chapter_dir in enumerate(chapter_dirs, 1):
                    out.write(f"\n{'='*80}\n")
                    out.write(f"CHAPTER {i:02d}: {chapter_dir}\n")
                    out.write(f"{'='*80}\n\n")
                    
                    # Read title.tex
                    title_path = os.path.join(chapter_dir, 'title.tex')
                    if os.path.exists(title_path):
                        with open(title_path, 'r', encoding='utf-8', errors='ignore') as f:
                            title_content = f.read().strip()
                            out.write(f"{title_content}\n\n")
                    else:
                        out.write(f"[title.tex not found]\n\n")
                    
                    # Read summary.tex
                    summary_path = os.path.join(chapter_dir, 'summary.tex')
                    if os.path.exists(summary_path):
                        with open(summary_path, 'r', encoding='utf-8', errors='ignore') as f:
                            summary_content = f.read().strip()
                            out.write(f"{summary_content}\n\n")
                    else:
                        out.write(f"[summary.tex not found]\n\n")
            
            file_size = os.path.getsize(output_file) / 1024  # KB
            print(f"[ok] Titles + Summaries saved: {output_file}")
            print(f"   Size: {file_size:.1f}KB, {len(chapter_dirs)} chapters")
            return True
            
        except Exception as e:
            print(f"[error] Title+Summary concatenation failed: {e}")
            return False
    
    def scale_pdf_to_7x10(self):
        """Scale the generated PDF from A4 to 7"×10" format."""
        pdf_file = f'{self.base_name}.pdf'
        scaled_file = f'{self.base_name}_7x10.pdf'
        scale_script = os.path.join(os.path.dirname(__file__), 'scale_pdf.py')
        
        if not os.path.exists(pdf_file):
            print(f"[error] Cannot scale: {pdf_file} not found!")
            return False
            
        if not os.path.exists(scale_script):
            print(f"[error] Cannot scale: {scale_script} not found!")
            return False
        
        print(f"\n[scale] SCALING PDF TO 7\"×10\"")
        print("=" * 30)
        
        try:
            # Run the scaling script
            result = subprocess.run([
                sys.executable, scale_script, pdf_file, scaled_file
            ], check=True, capture_output=False)
            
            if os.path.exists(scaled_file):
                scaled_size = os.path.getsize(scaled_file) / (1024*1024)
                print(f"[ok] Scaled PDF created: {scaled_file} ({scaled_size:.1f}MB)")
                return True
            else:
                print(f"[error] Scaling failed: {scaled_file} not created")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"[error] Scaling failed with error: {e}")
            return False

    def scale_pdf_to_trade(self):
        """Scale the generated PDF to US Trade size (6.14"×9.21")."""
        pdf_file = f'{self.base_name}.pdf'
        scaled_file = f'{self.base_name}_6.14x9.21_trade.pdf'
        scale_script = os.path.join(os.path.dirname(__file__), 'scale_pdf_to_trade.py')
        
        if not os.path.exists(pdf_file):
            print(f"[error] Cannot scale to trade: {pdf_file} not found!")
            return False
            
        if not os.path.exists(scale_script):
            print(f"[error] Cannot scale to trade: {scale_script} not found!")
            return False
        
        print(f"\n[scale] SCALING PDF TO US TRADE (6.14\"×9.21\")")
        print("=" * 45)
        
        try:
            result = subprocess.run([
                sys.executable, scale_script, pdf_file, scaled_file
            ], check=True, capture_output=False)
            
            if os.path.exists(scaled_file):
                scaled_size = os.path.getsize(scaled_file) / (1024*1024)
                print(f"[ok] Trade PDF created: {scaled_file} ({scaled_size:.1f}MB)")
                return True
            else:
                print(f"[error] Scaling failed: {scaled_file} not created")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"[error] Trade scaling failed with error: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(
        description='Real-time LaTeX compilation with optional PDF scaling',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 compile_realtime.py main.tex                    # Compile to A4
  python3 compile_realtime.py main.tex --scale            # Compile to A4, then scale to 7"×10"
  python3 compile_realtime.py main.tex --trade            # Compile and scale to US Trade (6.14"×9.21")
  python3 compile_realtime.py main.tex --scale --trade    # Compile, scale to both sizes
  python3 compile_realtime.py main.tex --concat           # Compile and generate concatenated text file
        """
    )
    
    parser.add_argument('tex_file', nargs='?', default='main.tex',
                      help='LaTeX file to compile (default: main.tex)')
    parser.add_argument('--scale', '--scale-to-7x10', action='store_true',
                      help='Scale the final PDF from A4 to 7"×10" format')
    parser.add_argument('--trade', '--scale-to-trade', action='store_true',
                      help='Scale the final PDF to US Trade size (6.14"×9.21")')
    parser.add_argument('--concat', '--concatenate', action='store_true',
                      help='Generate concatenated text file of all book content')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.tex_file):
        print(f"[error] Error: File '{args.tex_file}' not found!")
        exit(1)
    
    print(f"[info] Compiling: {args.tex_file}")
    if args.scale:
        print(f"[info] Will scale to 7\"×10\" after compilation")
    if args.trade:
        print(f"[info] Will scale to US Trade (6.14\"×9.21\") after compilation")
    if args.concat:
        print(f"[file] Will generate concatenated content file")
    
    compiler = RealTimeCompiler(args.tex_file)
    success = compiler.compile_document()
    
    if success and args.scale:
        scale_success = compiler.scale_pdf_to_7x10()
        if not scale_success:
            print("[warn]  Compilation succeeded but 7×10 scaling failed")
    
    if success and args.trade:
        trade_success = compiler.scale_pdf_to_trade()
        if not trade_success:
            print("[warn]  Compilation succeeded but trade scaling failed")
    
    if args.concat:
        compiler.concatenate_book_content()
    
    exit(0 if success else 1)

if __name__ == "__main__":
    main() 