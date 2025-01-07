from utils import get_git_revision_short_hash

OUTCOMES_PATH = 'tmp/outcomes.json'
WAGERS_PATH = f'tmp/wagers_{get_git_revision_short_hash()}.csv'