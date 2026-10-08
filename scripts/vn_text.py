# -*- coding: utf-8 -*-
"""Tiện ích tiếng Việt cho rà soát dữ liệu Eform: kiểm tra âm tiết, kiểu bỏ dấu, viết hoa."""
import re
import unicodedata

TONE_MARKS = {'̀', '́', '̃', '̉', '̣'}  # huyền, sắc, ngã, hỏi, nặng

ONSETS = ['ngh', 'ng', 'gh', 'gi', 'kh', 'nh', 'ph', 'qu', 'th', 'tr', 'ch',
          'b', 'c', 'd', 'đ', 'g', 'h', 'k', 'l', 'm', 'n', 'p', 'r', 's', 't', 'v', 'x', '']

_R = """
a ac ach ai am an ang anh ao ap at au ay
ăc ăm ăn ăng ăp ăt
âc âm ân âng âp ât âu ây
e ec em en eng eo ep et
ê êch êm ên ênh êp êt êu
i ia ich im in inh ip it iu iêc iêm iên iêng iêp iêt iêu
y yêm yên yêng yêt yêu
o oc oi om on ong op ot ooc oong
ô ôc ôi ôm ôn ông ôp ôt
ơ ơi ơm ơn ơp ơt
u uc ui um un ung up ut ua uôc uôi uôm uôn uông uôt
ư ưc ưi ưm ưn ưng ưt ưu ưa ươc ươi ươm ươn ương ươp ươt ươu
oa oac oach oai oam oan oang oanh oao oap oat oay oăc oăm oăn oăng oăt oe oen oeo oet
uân uâng uât uây uê uêch uênh uy uych uyên uyêt uynh uyp uyt uyu uơ uya
"""
RHYMES = set(_R.split())
# sau "qu" âm đệm đã nằm trong "qu": quả, quê, quy, quyết, quân...
QU_RHYMES = {r[1:] for r in RHYMES if r.startswith('u') and len(r) > 1} | {'a', 'ac', 'ach', 'ai', 'an', 'ang', 'anh', 'ao', 'at', 'ay', 'e', 'en', 'eo', 'et', 'ê', 'i', 'y', 'ơ'}


def nfc(s):
    return unicodedata.normalize('NFC', s)


def strip_tone(syl):
    """Bỏ dấu thanh, giữ dấu mũ/trăng/móc (â, ă, ơ, ư...)."""
    d = unicodedata.normalize('NFD', syl)
    tones = [c for c in d if c in TONE_MARKS]
    base = unicodedata.normalize('NFC', ''.join(c for c in d if c not in TONE_MARKS))
    return base, len(tones)


def is_vn_syllable(word):
    """True nếu 'word' (1 âm tiết, chữ thường) có cấu trúc âm tiết tiếng Việt hợp lệ (gần đúng)."""
    base, ntone = strip_tone(word.lower())
    if ntone > 1 or not base:
        return False
    for on in ONSETS:
        if not base.startswith(on):
            continue
        rest = base[len(on):]
        if on == 'qu':
            if rest in QU_RHYMES:
                return True
            continue
        if on == 'gi' and (rest == '' or rest in RHYMES or ('i' + rest) in RHYMES):
            return True
        if rest in RHYMES:
            # ràng buộc chính tả: k/gh/ngh chỉ đứng trước i, e, ê, y
            if on in ('k', 'gh', 'ngh') and not rest[:1] in ('i', 'e', 'ê', 'y'):
                continue
            if on in ('c', 'g', 'ng') and rest[:1] in ('i', 'e', 'ê') and on != 'g':
                continue
            return True
    return False


TOKEN_RE = re.compile(r"[A-Za-zÀ-ỹĐđ]+", re.UNICODE)


def suspicious_words(text):
    """Trả về các từ không giống âm tiết tiếng Việt (bỏ qua viết tắt in hoa, từ có số)."""
    out = []
    for w in TOKEN_RE.findall(nfc(text)):
        if w.isupper() and len(w) <= 8:      # TTHC, UBND, HĐND, QPPL...
            continue
        if not is_vn_syllable(w):
            out.append(w)
    return out


# Kiểu bỏ dấu cũ/mới ở các vần oa, oe, uy (hòa/hoà, khỏe/khoẻ, thủy/thuỷ)
OLD_NEW = [
    ('oà', 'òa'), ('oá', 'óa'), ('oả', 'ỏa'), ('oã', 'õa'), ('oạ', 'ọa'),
    ('oè', 'òe'), ('oé', 'óe'), ('oẻ', 'ỏe'), ('oẽ', 'õe'), ('oẹ', 'ọe'),
    ('uỳ', 'ùy'), ('uý', 'úy'), ('uỷ', 'ủy'), ('uỹ', 'ũy'), ('uỵ', 'ụy'),
]
_END = r"(?![a-zà-ỹđ])"   # chỉ áp dụng khi vần đứng cuối âm tiết (hòa, không áp cho hoàn, thuyết)
_BEG = r"(?<![qQ])"        # "qu" là phụ âm đầu: quỹ, quý, quả không thuộc quy tắc này


def tone_style(text):
    """Đếm số chỗ bỏ dấu kiểu cũ / kiểu mới trong text."""
    t = nfc(text).lower()
    old = sum(len(re.findall(_BEG + re.escape(o) + _END, t)) for o, n in OLD_NEW)
    new = sum(len(re.findall(_BEG + re.escape(n) + _END, t)) for o, n in OLD_NEW)
    return old, new


def to_style(text, style):
    """Chuyển các vần oa/oe/uy cuối âm tiết sang kiểu bỏ dấu 'old' hoặc 'new' (giữ hoa/thường)."""
    t = nfc(text)
    pairs = OLD_NEW if style == 'new' else [(n, o) for o, n in OLD_NEW]
    for a, b in pairs:
        for A, Bv in ((a, b), (a.capitalize(), b.capitalize()), (a.upper(), b.upper())):
            t = re.sub(_BEG + re.escape(A) + _END, Bv, t)
    return t


PROPER = ['Việt Nam', 'Hồ Chí Minh', 'Hà Nội', 'Nhà nước', 'Chính phủ', 'Quốc hội', 'Đảng']
AGENCY_HEADS = ('Sở ', 'Bộ ', 'Ủy ban', 'Uỷ ban', 'UBND', 'Văn phòng', 'Văn phong', 'Trung tâm', 'Ban ', 'Cục ', 'Chi cục', 'Phòng ', 'Thanh tra')


def sentence_case(text):
    """Viết hoa chữ đầu, hạ chữ thường các từ viết hoa giữa câu (trừ viết tắt và danh từ riêng phổ biến)."""
    t = nfc(text).strip()
    protected = {}
    for i, p in enumerate(PROPER):
        if p in t:
            key = f'\x00{i}\x00'
            t = t.replace(p, key)
            protected[key] = p
    words = t.split(' ')
    out = []
    for i, w in enumerate(words):
        if i > 0 and w[:1].isupper() and not (w.isupper() and len(w) > 1) and '\x00' not in w:
            w = w[:1].lower() + w[1:]
        out.append(w)
    t = ' '.join(out)
    if t[:1].islower():
        t = t[:1].upper() + t[1:]
    for k, v in protected.items():
        t = t.replace(k, v)
    return t
