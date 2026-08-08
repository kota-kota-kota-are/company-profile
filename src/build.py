#!/usr/bin/env python3
"""3パートを統合し、使用文字だけのZen Maru Gothicを埋め込んで1ページに仕上げる。"""
import re, sys, base64, pathlib, urllib.parse, urllib.request

D = pathlib.Path(__file__).parent
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# ---------- 1. パートを読む ----------
parts = []
for n in (1, 2, 3):
    f = D / f"part{n}.html"
    if not f.exists():
        sys.exit(f"missing: {f}")
    parts.append(f.read_text())
body = "\n".join(parts)

# ---------- 2. 実際に使われている文字を集める ----------
visible = re.sub(r"<style.*?</style>|<script.*?</script>", "", body, flags=re.S)
visible = re.sub(r"<[^>]+>", " ", visible)
chars = set(visible)
chars |= set(chr(c) for c in range(0x3041, 0x3097))   # ひらがな全域
chars |= set(chr(c) for c in range(0x30A1, 0x30F7))   # カタカナ全域
chars |= set("ー・、。「」『』（）〜％円月年日／：×→←↓↑◎△○●■□★☆＋－")
chars |= set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
chars |= set(".,/:;-—–()%&#!?'\"")
chars = {c for c in chars if c.strip() and ord(c) > 0x1F}
subset = "".join(sorted(chars))
print(f"サブセット文字数: {len(subset)}")

# ---------- 3. Google Fonts からサブセットを取得 ----------
url = ("https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;700&text="
       + urllib.parse.quote(subset))
css = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read().decode()

faces = []
for w, u in re.findall(r"font-weight:\s*(\d+);\s*src:\s*url\((https://[^)]+)\)", css):
    data = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60).read()
    print(f"  weight {w}: {len(data)//1024} KB")
    faces.append('@font-face{font-family:"ZenMaru";font-style:normal;font-weight:%s;'
                 'font-display:swap;src:url(data:font/woff2;base64,%s) format("woff2")}'
                 % (w, base64.b64encode(data).decode()))
if len(faces) < 2:
    sys.exit("フォント取得に失敗（ウェイトが揃わない）")
font_css = "\n".join(faces)

# ---------- 4. ロゴ ----------
light = "data:image/png;base64," + (D / "logo-light.b64").read_text().strip()
dark = "data:image/png;base64," + (D / "logo-dark.b64").read_text().strip()
body = body.replace('src="LOGO_SRC"', f'src="{light}" data-logo')
body = body.replace("src='LOGO_SRC'", f'src="{light}" data-logo')

TOKENS = """
:root{
  --page:#FEFDFB; --band:#F5F2E9; --tint:#E4EBC4;
  --text:#201F1F; --mute:#5A5A54;
  --accent:#B2C250; --accent-text:#386641;
  --rule:rgba(32,31,31,.13);
}
@media (prefers-color-scheme:dark){
  :root{
    --page:#15180F; --band:#1D2117; --tint:#252A1C;
    --text:#F2F0E6; --mute:#A9A89C;
    --accent:#B2C250; --accent-text:#C3D169;
    --rule:rgba(242,240,230,.16);
  }
}
:root[data-theme="dark"]{
  --page:#15180F; --band:#1D2117; --tint:#252A1C;
  --text:#F2F0E6; --mute:#A9A89C;
  --accent:#B2C250; --accent-text:#C3D169;
  --rule:rgba(242,240,230,.16);
}
:root[data-theme="light"]{
  --page:#FEFDFB; --band:#F5F2E9; --tint:#E4EBC4;
  --text:#201F1F; --mute:#5A5A54;
  --accent:#B2C250; --accent-text:#386641;
  --rule:rgba(32,31,31,.13);
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0; background:var(--page); color:var(--text);
  font-family:"ZenMaru","Hiragino Maru Gothic ProN","Hiragino Sans",system-ui,sans-serif;
  font-feature-settings:"palt" 1; line-height:1.9;
  overflow-x:hidden;
}
img{max-width:100%}
@media (prefers-reduced-motion:reduce){*{transition:none !important;animation:none !important}}
@media print{
  body{background:#fff !important; color:#111 !important}
  @page{margin:14mm}
}
"""

out = f"""<title>創発の種 — 会社紹介</title>
<style>{font_css}
{TOKENS}</style>

{body}

<script>
(function(){{
  var LIGHT = "{light}", DARK = "{dark}";
  var mq = window.matchMedia('(prefers-color-scheme: dark)');
  function isDark(){{
    var t = document.documentElement.getAttribute('data-theme');
    if (t === 'dark') return true;
    if (t === 'light') return false;
    return mq.matches;
  }}
  function sync(){{
    var src = isDark() ? DARK : LIGHT;
    document.querySelectorAll('img[data-logo]').forEach(function(el){{
      if (el.getAttribute('src') !== src) el.setAttribute('src', src);
    }});
  }}
  sync();
  if (mq.addEventListener) mq.addEventListener('change', sync);
  new MutationObserver(sync).observe(document.documentElement, {{attributes:true, attributeFilter:['data-theme']}});
  window.addEventListener('beforeprint', function(){{
    document.querySelectorAll('img[data-logo]').forEach(function(el){{ el.setAttribute('src', LIGHT); }});
  }});
}})();
</script>
"""

target = D / "company-profile.html"
target.write_text(out)
print(f"built: {target} ({len(out)//1024} KB)")

# ---------- 5. 検証 ----------
for tag in ("div", "section", "span", "button", "table", "tr", "td", "th"):
    o = len(re.findall(r"<" + tag + r"\b", out))
    c = len(re.findall(r"</" + tag + r">", out))
    print(f"  {tag}: {o}/{c}", "OK" if o == c else "*** 不一致 ***")
leftover = out.count("LOGO_SRC")
print(f"  LOGO_SRC残り: {leftover}", "OK" if leftover == 0 else "*** 未置換 ***")
bare = re.findall(r"\n\s*(section|h1|h2|h3|p|table|button)\s*\{", out)
print(f"  スコープ外セレクタ: {len(bare)}", "OK" if not bare else f"*** {set(bare)} ***")
