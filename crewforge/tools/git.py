"""Git operations tool for agents."""

from pathlib import Path
from typing import Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

try:
    from git import Repo, InvalidGitRepositoryError, GitCommandError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    Repo = None


class GitInitInput(BaseModel):
    """Input schema for git init."""

    repo_path: str = Field(..., description="Path to initialize as a git repository")
    initial_branch: str = Field(default="main", description="Name of the initial branch")


class GitInitTool(BaseTool):
    """Tool to initialize a git repository."""

    name: str = "git_init"
    description: str = "Initialize a new git repository in the specified directory."
    args_schema: Type[BaseModel] = GitInitInput

    def _run(self, repo_path: str, initial_branch: str = "main") -> str:
        """Initialize git repository."""
        if not GIT_AVAILABLE:
            return "Error: GitPython is not installed."

        try:
            path = Path(repo_path)
            path.mkdir(parents=True, exist_ok=True)
            repo = Repo.init(path, initial_branch=initial_branch)
            return f"Initialized git repository at '{repo_path}' with branch '{initial_branch}'"
        except Exception as e:
            return f"Error initializing repository: {str(e)}"


class GitCommitInput(BaseModel):
    """Input schema for git commit."""

    repo_path: str = Field(..., description="Path to the git repository")
    message: str = Field(..., description="Commit message")
    add_all: bool = Field(default=True, description="Add all changes before committing")


class GitCommitTool(BaseTool):
    """Tool to commit changes."""

    name: str = "git_commit"
    description: str = "Stage and commit changes to the git repository."
    args_schema: Type[BaseModel] = GitCommitInput

    def _run(self, repo_path: str, message: str, add_all: bool = True) -> str:
        """Commit changes."""
        if not GIT_AVAILABLE:
            return "Error: GitPython is not installed."

        try:
            repo = Repo(repo_path)

            if add_all:
                repo.git.add(A=True)

            # Check if there are changes to commit
            if not repo.is_dirty() and not repo.untracked_files:
                return "No changes to commit."

            commit = repo.index.commit(message)
            return f"Committed: {commit.hexsha[:8]} - {message}"
        except InvalidGitRepositoryError:
            return f"Error: '{repo_path}' is not a git repository."
        except Exception as e:
            return f"Error committing: {str(e)}"


class GitBranchInput(BaseModel):
    """Input schema for git branch operations."""

    repo_path: str = Field(..., description="Path to the git repository")
    branch_name: str = Field(..., description="Name of the branch")
    checkout: bool = Field(default=True, description="Checkout the branch after creating")


class GitCreateBranchTool(BaseTool):
    """Tool to create a new branch."""

    name: str = "git_create_branch"
    description: str = "Create a new git branch and optionally checkout."
    args_schema: Type[BaseModel] = GitBranchInput

    def _run(self, repo_path: str, branch_name: str, checkout: bool = True) -> str:
        """Create branch."""
        if not GIT_AVAILABLE:
            return "Error: GitPython is not installed."

        try:
            repo = Repo(repo_path)

            # Check if branch exists
            if branch_name in [b.name for b in repo.branches]:
                if checkout:
                    repo.git.checkout(branch_name)
                    return f"Branch '{branch_name}' already exists. Checked out."
                return f"Branch '{branch_name}' already exists."

            # Create branch
            new_branch = repo.create_head(branch_name)

            if checkout:
                new_branch.checkout()
                return f"Created and checked out branch '{branch_name}'"
            return f"Created branch '{branch_name}'"
        except InvalidGitRepositoryError:
            return f"Error: '{repo_path}' is not a git repository."
        except Exception as e:
            return f"Error creating branch: {str(e)}"


class GitCheckoutInput(BaseModel):
    """Input schema for git checkout."""

    repo_path: str = Field(..., description="Path to the git repository")
    branch_name: str = Field(..., description="Name of the branch to checkout")


class GitCheckoutTool(BaseTool):
    """Tool to checkout a branch."""

    name: str = "git_checkout"
    description: str = "Checkout an existing git branch."
    args_schema: Type[BaseModel] = GitCheckoutInput

    def _run(self, repo_path: str, branch_name: str) -> str:
        """Checkout branch."""
        if not GIT_AVAILABLE:
            return "Error: GitPython is not installed."

        try:
            repo = Repo(repo_path)
            repo.git.checkout(branch_name)
            return f"Checked out branch '{branch_name}'"
        except InvalidGitRepositoryError:
            return f"Error: '{repo_path}' is not a git repository."
        except Exception as e:
            return f"Error checking out branch: {str(e)}"


class GitMergeInput(BaseModel):
    """Input schema for git merge."""

    repo_path: str = Field(..., description="Path to the git repository")
    source_branch: str = Field(..., description="Branch to merge from")
    target_branch: str = Field(default="main", description="Branch to merge into")


class GitMergeTool(BaseTool):
    """Tool to merge branches."""

    name: str = "git_merge"
    description: str = "Merge a source branch into a target branch."
    args_schema: Type[BaseModel] = GitMergeInput

    def _run(
        self, repo_path: str, source_branch: str, target_branch: str = "main"
    ) -> str:
        """Merge branches."""
        if not GIT_AVAILABLE:
            return "Error: GitPython is not installed."

        try:
            repo = Repo(repo_path)

            # Checkout target branch
            repo.git.checkout(target_branch)

            # Merge source branch
            repo.git.merge(source_branch)

            return f"Merged '{source_branch}' into '{target_branch}'"
        except InvalidGitRepositoryError:
            return f"Error: '{repo_path}' is not a git repository."
        except GitCommandError as e:
            return f"Merge conflict or error: {str(e)}"
        except Exception as e:
            return f"Error merging: {str(e)}"


class GitStatusInput(BaseModel):
    """Input schema for git status."""

    repo_path: str = Field(..., description="Path to the git repository")


class GitStatusTool(BaseTool):
    """Tool to get git status."""

    name: str = "git_status"
    description: str = "Get the current git status of the repository."
    args_schema: Type[BaseModel] = GitStatusInput

    def _run(self, repo_path: str) -> str:
        """Get git status."""
        if not GIT_AVAILABLE:
            return "Error: GitPython is not installed."

        try:
            repo = Repo(repo_path)

            status_parts = []
            status_parts.append(f"Current branch: {repo.active_branch.name}")

            # Check for uncommitted changes
            if repo.is_dirty():
                status_parts.append("\nModified files:")
                for item in repo.index.diff(None):
                    status_parts.append(f"  M {item.a_path}")

            # Check for staged changes
            staged = repo.index.diff("HEAD")
            if staged:
                status_parts.append("\nStaged changes:")
                for item in staged:
                    status_parts.append(f"  S {item.a_path}")

            # Check for untracked files
            if repo.untracked_files:
                status_parts.append("\nUntracked files:")
                for f in repo.untracked_files:
                    status_parts.append(f"  ? {f}")

            if len(status_parts) == 1:
                status_parts.append("\nWorking tree clean.")

            return "\n".join(status_parts)
        except InvalidGitRepositoryError:
            return f"Error: '{repo_path}' is not a git repository."
        except Exception as e:
            return f"Error getting status: {str(e)}"


class GitDeleteBranchInput(BaseModel):
    """Input schema for git branch deletion."""

    repo_path: str = Field(..., description="Path to the git repository")
    branch_name: str = Field(..., description="Name of the branch to delete")
    force: bool = Field(default=False, description="Force delete unmerged branch")


class GitDeleteBranchTool(BaseTool):
    """Tool to delete a branch."""

    name: str = "git_delete_branch"
    description: str = "Delete a git branch."
    args_schema: Type[BaseModel] = GitDeleteBranchInput

    def _run(self, repo_path: str, branch_name: str, force: bool = False) -> str:
        """Delete branch."""
        if not GIT_AVAILABLE:
            return "Error: GitPython is not installed."

        try:
            repo = Repo(repo_path)

            if repo.active_branch.name == branch_name:
                return f"Error: Cannot delete the currently checked out branch '{branch_name}'"

            if force:
                repo.git.branch("-D", branch_name)
            else:
                repo.git.branch("-d", branch_name)

            return f"Deleted branch '{branch_name}'"
        except InvalidGitRepositoryError:
            return f"Error: '{repo_path}' is not a git repository."
        except Exception as e:
            return f"Error deleting branch: {str(e)}"


class GitTool:
    """Collection of git tools."""

    @staticmethod
    def get_tools() -> list[BaseTool]:
        """Get all git tools."""
        return [
            GitInitTool(),
            GitCommitTool(),
            GitCreateBranchTool(),
            GitCheckoutTool(),
            GitMergeTool(),
            GitStatusTool(),
            GitDeleteBranchTool(),
        ]
