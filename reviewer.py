import sys
import subprocess
import requests
import os
import re
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment variables from .env file
load_dotenv()
OLLAMA_URL = os.getenv("OLLAMA_URL")
AI_MODEL = os.getenv("AI_MODEL")
CHUNK_LIMIT = int(os.getenv("CHUNK_LIMIT"))

# Initialize console
console = Console()

class AIReviewer:
    def __init__(self, target_branch, source_branch):
        self.target_branch = target_branch
        self.source_branch = source_branch
        self.report_lines = []

    def run_command(self, cmd):
        """Execute a shell command and return the output."""
        
        try:
            return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Git Error:[/bold red] {e}")
            sys.exit(1)

    def get_changed_files(self, merge_base):
        """Identifies which files have changed"""
        stats = self.run_command(f"git diff --name-only {merge_base} {self.source_branch}")
        return [f for f in stats.split('\n') if f and not f.endswith(('.lock', '.png', '.jpg', '.svg'))]

    def get_file_diff(self, merge_base, file_name):
        """Fetches the raw diff for a specific file."""
        return self.run_command(f"git diff {merge_base} {self.source_branch} -- {file_name}")

    def split_into_hunks(self, diff_content):
        """
        Splits a large diff into Git 'hunks' (logical blocks of changes).
        Regex looks for the diff header: @@ -10,4 +10,5 @@
        """
        # Split by tge git hunk header pattern
        hunks = re.split(r'(^@@\s.*?\s@@)', diff_content, flags=re.MULTILINE)

        # Reassemble header+content pairs
        assembled_hunks = []
        if len(hunks) > 1:
            # hunks[0] is usually the file header info (diff --git...), keep it for context
            file_header = hunks[0]
            for i in range(1, len(hunks), 2):
                header = hunks[i]
                code = hunks[i+1] if i+1 < len(hunks) else ""
                assembled_hunks.append((file_header + "\n" + header + code))
        else:
            assembled_hunks = [diff_content]
        
        return assembled_hunks

    def ask_llm(self, file_name, content, is_partial=False):
        """Sends the payload to Dockerized Ollama"""
        context_note = "(Partial Hunk Review)" if is_partial else "(Full File Review)"

        prompt = f"""
            You are an expert code reviewer. Review this git diff for '{file_name}' {context_note}. 

            Guidance:
                - Identify logic errors, security risks, or dirty code.
                - IGNORE trivial changes (whitespace, imports).
                - Be concise. Use bullet points.
                - If the code is good, reply ONLY with "LGTM".
        
            DIFF:
            ```diff
            {content}
            ```
        """

        payload = {
            "model": AI_MODEL,
            "messages": [{"role": "system", "content": prompt}],
            "stream": False
        }

        try:
            resp = requests.post(OLLAMA_URL, json=payload)
            resp.raise_for_status()
            
            choices = resp.json().get('choices', [])
            if choices:
                return choices[0].get('message', {}).get('content', '').strip()
            else:
                return resp.json().get('response', '').strip()
        except Exception as e:
            return f"LLM Error: {str(e)}"

    def generate_report(self):
        console.print(f"[bold blue]Starting Review:[/bold blue] {self.target_branch} <- {self.source_branch}")

        # 1. Find merge base
        merge_base = self.run_command(f"git merge-base origin/{self.target_branch} {self.source_branch}")
        files = self.get_changed_files(merge_base)

        if not files:
            console.print("[bold yellow]No changes detected.[/bold yellow]")
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[Progress.description]{task.description}"),
            transient=True
        ) as progress:

            task = progress.add_task("[green]Analyzing files...", total=len(files))

            for file_name in files:
                progress.update(task, description=f"Reviewing {file_name}...")

                raw_diff = self.get_file_diff(merge_base, file_name)
                
                # Decision: Send full file or split into hunks?
                if len(raw_diff) > CHUNK_LIMIT:
                    hunks = self.split_into_hunks(raw_diff)
                    file_comments = []

                    for i, hunk in enumerate(hunks):
                        progress.update(task, description=f"Reviewing {filename} (Hunk {i+1}/{len(hunks)})...")
                        review = self.ask_llm(file_name, hunk, is_partial=True)
                        if "LGTM" not in review:
                            file_comments.append(f"**Hunk {i+1}:**\n{review}")

                        final_review = "\n\n".join(file_comments) if file_comments else "LGTM"
                else:
                    final_review = self.ask_llm(file_name, raw_diff)

                # Store the result
                if "LGTM" not in final_review:
                    self.report_lines.append(f"## `{file_name}`\n{final_review}\n")
                    console.print(f"[bold red]Issues in {file_name}[/bold red]")
                else:
                    console.print(f"[bold green]LGTM for {file_name}[/bold green]")

                # progress.update(task, advance=1)
                progress.advance(task)
        
        # Final output
        self.save_report()

    
    def save_report(self):
        if not self.report_lines:
            console.print("\n[bold green] No issues found. The code looks great![/bold green]")
            return

        content = f"# AI Code Review: {self.source_branch}\n\n" + "\n---\n".join(self.report_lines)

        with open("PR_REVIEW.md", "w", encoding="utf-8") as f:
            f.write(content)

        console.print("\n[bold yellow]Review Complete![/bold yellow] Report saved to: [underline]PR_REVIEW.md[/underline]")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        console.print("Usage: python reviewer.py <target_branch> <source_branch>")
        sys.exit(1)
    
    target_branch = sys.argv[1]
    source_branch = sys.argv[2]
    
    reviewer = AIReviewer(target_branch, source_branch)
    reviewer.generate_report()
        