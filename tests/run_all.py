"""Standalone test runner — no pytest dependency required."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

results = []

# 1. Likeness
from app.game.likeness import calculate_likeness
ok = all([
    calculate_likeness('REACTOR','REACTOR')==7,
    calculate_likeness('AAAAAAA','ZZZZZZZ')==0,
    calculate_likeness('reactor','REACTOR')==7,
    calculate_likeness('','')==0,
    calculate_likeness('ABCD','DCBA')==0,
])
results.append(('likeness', ok))

# 2. Word list
from app.game.word_list import WORDS, get_words_by_length
ok = (len(WORDS) >= 50
      and all(7<=len(w)<=10 and w==w.upper() and w.isalpha() for w in WORDS)
      and len(WORDS)==len(set(WORDS))
      and all(len(get_words_by_length(l))>=12 for l in range(7,11)))
results.append(('word_list', ok))

# 3. Bracket tricks
from app.game.bracket_tricks import find_bracket_pairs, apply_dud_removal, apply_allowance_replenishment
ok = (len(find_bracket_pairs('(a)'))==1
      and len(find_bracket_pairs(''))==0
      and apply_allowance_replenishment(1,4)==4
      and apply_dud_removal(['A'],'A',set()) is None)
for _ in range(50):
    r = set()
    v = apply_dud_removal(['A','B','C'], 'A', r)
    if v == 'A': ok = False
results.append(('bracket_tricks', ok))

# 4. Puzzle generator
from app.game.puzzle_generator import generate_puzzle
ok = True
for _ in range(5):
    p = generate_puzzle()
    if len(set(len(w) for w in p.candidates)) != 1: ok = False
    if p.correct_password not in p.candidates: ok = False
    if len(p.layout.left_column) != len(p.layout.right_column): ok = False
    for wp in p.layout.word_positions:
        col = p.layout.left_column if wp.column==0 else p.layout.right_column
        if col[wp.row][wp.start_col:wp.start_col+len(wp.word)] != wp.word: ok = False
results.append(('puzzle_generator', ok))

# 5. Game state
from app.game.game_state import GameState, GamePhase
ok = True
gs = GameState()
if gs.phase != GamePhase.BOOT: ok = False
gs.advance_to_menu()
if gs.phase != GamePhase.MENU: ok = False
gs.start_game()
if gs.phase != GamePhase.PLAYING: ok = False
r = gs.guess(gs.correct_password)
if not r.is_correct or not gs.is_authenticated: ok = False
gs2 = GameState(initial_attempts=2); gs2.advance_to_menu(); gs2.start_game()
wrongs = [w for w in gs2.candidates if w != gs2.correct_password]
gs2.guess(wrongs[0]); gs2.guess(wrongs[1])
if not gs2.is_locked_out: ok = False
try: gs2.guess(wrongs[0]); ok = False
except RuntimeError: pass
gs3 = GameState(); gs3.advance_to_menu(); gs3.start_game()
try: gs3.guess('ZZZZZZ'); ok = False
except ValueError: pass
results.append(('game_state', ok))

# 6. Config
from app.config.settings import load_config
cfg = load_config(['--development','--mock-auth','--no-crt','--skip-boot'])
ok = (cfg.system.development_mode and cfg.system.mock_auth
      and not cfg.display.crt_effects and not cfg.boot.show_animation)
results.append(('config', ok))

# 7. Mock auth
from app.auth.authenticator import MockAuthenticator
a = MockAuthenticator()
ok = a.authenticate('dev','dev') and not a.authenticate('x','y')
results.append(('mock_auth', ok))

# 8. Screen transitions
from PyQt6.QtWidgets import QApplication
from app.ui.main_window import MainWindow, SCREEN_MENU, SCREEN_HACKING, SCREEN_SYSTEM_LOGIN, SCREEN_LOCKOUT
app = QApplication(sys.argv)
cfg2 = load_config(['--development','--mock-auth','--skip-boot','--no-crt'])
w = MainWindow(cfg2); w.show()
ok = w._stack.currentIndex() == SCREEN_MENU
w._on_login_selected(); ok = ok and w._stack.currentIndex() == SCREEN_HACKING
w._on_system_login_requested(); ok = ok and w._stack.currentIndex() == SCREEN_SYSTEM_LOGIN
w._on_system_login_cancelled(); ok = ok and w._stack.currentIndex() == SCREEN_HACKING
w._on_return_to_menu(); ok = ok and w._stack.currentIndex() == SCREEN_MENU
w._on_login_selected(); w._on_lockout(); ok = ok and w._stack.currentIndex() == SCREEN_LOCKOUT
results.append(('screen_transitions', ok))
app.quit()
try: os.unlink('/tmp/robco-greeter-lockout')
except: pass

# Print
print()
all_ok = True
for name, ok in results:
    s = 'PASS' if ok else 'FAIL'
    if not ok: all_ok = False
    print(f'  [{s}] {name}')
print()
print('=== ALL TESTS PASSED ===' if all_ok else '!!! SOME TESTS FAILED !!!')
sys.exit(0 if all_ok else 1)
