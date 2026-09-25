[![Release](https://img.shields.io/github/v/release/sametbrr/llm-wiki-manager?display_name=tag&sort=semver)](https://github.com/sametbrr/llm-wiki-manager/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/agentskills.io-compatible-blue)](https://agentskills.io)

# LLM Wiki Manager

Kişisel, LLM tarafından yönetilen bir wiki oluşturmak ve sürdürmek için Claude Code skill'i — LLM tüm yazma, çapraz referans ve kayıt tutma işlerini yaparken siz kaynakları seçip sorular sorarsınız.

> 🇬🇧 For English see [README.md](README.md)

---

## Hızlı Başlangıç

```bash
git clone https://github.com/sametbrr/llm-wiki-manager ~/.claude/skills/llm-wiki-manager
```

Araştırma klasörünüzde yeni bir Claude Code oturumu başlatın:

```bash
mkdir ~/research/konum && cd ~/research/konum && claude
> "Burada bir LLM wiki oluştur. Konu: beslenme bilimi tarihi."
```

---

## Özellikler

RAG'dan farklı olarak — LLM'nin her sorguda ham belgelerden cevap yeniden keşfettiği yaklaşım — bu pattern LLM'nin ham kaynakları kalıcı, birbiriyle bağlantılı bir markdown wiki'sine **derlemesini** sağlar. Her yeni kaynak mevcut sayfaları zenginleştirir. Çapraz referanslar hevesle kurulur. Çelişkiler işaretlenir. Bilgi zamanla birikerek büyür.

[Karpathy'nin LLM Wiki pattern'ini](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 8 çalışma modu (çok-wiki yönlendirme dahil), 5 idempotent Python scripti, 8 sayfa şablonu ve 11 referans belgeyle tam bir Claude Code skill'i olarak uygular.

```
Bu pattern olmadan          Bu pattern ile
──────────────────          ──────────────
Sorgu 1 → 50 belge yeniden okunur    Sorgu 1 → derlenmiş wiki okunur (zaten sentezlendi)
Sorgu 2 → 50 belge yeniden okunur    Sorgu 2 → güncel wiki okunur (çapraz referanslar hazır)
Sorgu 3 → 50 belge yeniden okunur    Sorgu 3 → güncel wiki okunur (çelişkiler işaretlendi)
```

---

## Gereksinimler

- Claude Code veya herhangi bir [agentskills.io](https://agentskills.io) uyumlu agent
- Python 3.9+ (yalnızca stdlib, dahil 5 script için — pip kurulumu gerekmez)

---

## Kurulum

**Seçenek 1 — git clone (önerilen)**
```bash
git clone https://github.com/sametbrr/llm-wiki-manager ~/.claude/skills/llm-wiki-manager
```

**Seçenek 2 — GitHub CLI** (gh CLI v2.90+ gerektirir)
```bash
gh skill install sametbrr/llm-wiki-manager
```

**Seçenek 3 — .skill dosyası**
```bash
curl -L -o llm-wiki-manager.skill \
  https://github.com/sametbrr/llm-wiki-manager/releases/latest/download/llm-wiki-manager.skill
unzip llm-wiki-manager.skill -d ~/.claude/skills/llm-wiki-manager
```

Kurulumdan sonra yeni bir Claude Code oturumu başlatın. Skill ilgili olduğunda otomatik yüklenir.

---

## Kullanım

Skill, doğal dilden hangi modun uygulanacağını otomatik olarak algılar. Slash komutu gerekmez.

### Modlar

| Mod | Tetikleyici örnekler | Ne olur |
|---|---|---|
| **Bootstrap** | "Wiki kur", "burada bir bilgi tabanı başlat" | `raw/`, `wiki/`, `CLAUDE.md`'yi şablonlardan oluşturur |
| **Ingest** | "Bu PDF'i wiki'ye ekle", "X'i az önce okudum, kaydet" | Kaynağı okur → özet yazar → varlık/kavram sayfalarını günceller → indeksler → loglar |
| **Query** | "Wiki X hakkında ne diyor?", "X ile Y'yi karşılaştır" | İndeksi okur → aday sayfalar → alıntılı cevap sentezler → kaydetmeyi teklif eder |
| **Update** | "Smith 2024, Keys 1980'in yerini aldı, wiki'yi güncelle" | Tüm sayfalarda semantik tarama → sayfa başına diff-before-write → tek log girişi |
| **Lint** | "Wiki'yi kontrol et", "bir sorun var mı?" | `lint_wiki.py` çalıştırır → `wiki/reports/lint-YYYY-MM-DD.md` kaydeder → indeks ve log'a ekler |
| **Schema-evolve** | "Bundan böyle her zaman X yapmalıyız" | `CLAUDE.md`'yi günceller, böylece gelecek oturumlar bu kuralı bilir |
| **Multi-wiki** | "Bunu global wiki'me ekle", "global wiki hakkında ne diyor" | Proje `CLAUDE.md`'sindeki bildirgeye göre wiki'ler arasında yönlendirir |
| **Teach** | "Bu pattern nasıl çalışıyor?", "LLM wiki fikrini açıkla" | Pattern'i açıklar, RAG ile karşılaştırır, somut bir örnek üzerinden anlatır |

### Tam adımlar

```bash
# 1. Araştırma klasörünüze gidin
mkdir ~/research/konum && cd ~/research/konum && claude

# 2. Wiki'yi başlatın
> "Burada bir LLM wiki oluştur. Konu: beslenme bilimi tarihi."

# 3. Kaynak ekleyin
cp ~/Downloads/kitap-2008.pdf raw/

# 4. İçeri aktarın
> "Kitabı wiki'ye ekle"

# 5. Sorular sorun
> "Wiki, beslenmecilik hakkında ne diyor?"

# 6. Sağlık kontrolü (wiki/reports/ içine tarihli rapor kaydeder)
> "Wiki'yi lint et"
```

---

## Üç Katmanlı Model

```
your-wiki/
├── CLAUDE.md          # Şema — bu wiki için kurallar (zamanla birlikte evrilir)
├── raw/               # SİZİN katmanınız — değiştirilemez kaynaklar. LLM okur, asla yazmaz.
└── wiki/              # LLM katmanı — tüm sayfalar LLM tarafından yazılır ve sürdürülür
    ├── index.md       # İçerik kataloğu (her içe aktarmada güncellenir)
    ├── log.md         # Sadece ekleme yapılan işlem günlüğü (grep'lenebilir)
    ├── hot.md         # Sıcak önbellek — son eklenen kaynaklar ve aktif referanslar
    ├── sources/       # İçe aktarılan her kaynak için bir özet sayfası
    ├── entities/      # Kişiler, kuruluşlar, yerler, ürünler
    ├── concepts/      # Fikirler, teoriler, çerçeveler, terimler
    ├── notes/         # Kaydedilen sorgu cevapları ve serbest sayfalar
    └── reports/       # Otomatik oluşturulan tarihli lint raporları
```

**İş bölümü:**

| Siz yaparsınız | LLM yapar |
|---|---|
| Kaynakları seçin (ne okunacağına karar verin) | Kaynakları baştan sona okur |
| Sorular sorun, yönlendirin | Özetler, varlık ve kavram sayfaları yazar |
| Wiki'yi inceleyin, linkleri takip edin | Çapraz referansları yerinde günceller |
| Neyin önemli olduğuna karar verin | index.md ve log.md'yi sürdürür |
| `raw/` dizinine sahip olun | Çelişkileri işaretler, boşlukları ortaya çıkarır |

Wiki sayfalarını neredeyse hiç elinizle yazmazsınız. LLM kayıt işlemlerini yapar — bu, wiki'nin çökmek yerine birikmesini sağlayan şeydir.

---

## Temel Disiplinler

1. **LLM `wiki/`'ye sahiptir. Siz `raw/`'a.** İstisna yok.
2. **Her işlem `log.md`'ye loglanır** — `append_log.py` ile. Grep'lenebilir: `grep "^## \[" log.md | tail -20`
3. **Her yeni veya güncellenen sayfa `index.md`'ye dokunur** — `update_index.py` ile. Eski indeks = kaybolmuş hissettiren wiki.
4. **Çapraz referansları agresif olarak kurun.** Bir kaynak zaten sayfası olan bir varlıktan bahsediyorsa o sayfayı güncelleyin. Bağlantıları örtük bırakmayın.
5. **`raw/`'a atıfta bulunun.** Her iddia belirli bir kaynak dosyasına kadar izlenebilir olmalıdır.
6. **Çelişkileri işaretleyin, üzerine yazmayın.** Yeni kaynak eski iddiaya katılmıyor mu? Her ikisi de kaynağıyla işaretli kalır, `> [!warning] Sources disagree` notuyla.
7. **Şema `CLAUDE.md`'de yaşar.** Bir kural işe yarıyorsa yazın. Bir sonraki oturum bilgili başlar.

---

## İçinde Neler Var

### Scriptler (Python stdlib, bağımlılık yok, hepsi idempotent)

| Script | Amaç |
|---|---|
| `scripts/init_wiki.py` | Yeni bir wiki oluşturur — `raw/`, `wiki/`, `CLAUDE.md`, `index.md`, `log.md` ve `hot.md` oluşturur. İdempotent. |
| `scripts/append_log.py` | `log.md`'ye `## [YYYY-MM-DD] eylem \| başlık` girişi ekler. Esnek log yolu tespitini destekler. |
| `scripts/update_index.py` | `index.md`'de bir kategori altına giriş ekler veya günceller. (kategori, başlık) çiftine göre upsert yapar. |
| `scripts/lint_wiki.py` | Sağlık kontrolü. Hem standart markdown hem Obsidian wiki-link (`[[...]]`) formatında yetim sayfaları ve indeks kaymasını tespit eder. Varsayılan: `wiki/reports/lint-<bugün>.md` yazar ve otomatik takip eder. |
| `scripts/migrate_wiki.py` | Şema yükseltme (v1 → v2). `index.md`'yi tekilleştirir, `hot.md`'deki tarihli changelog bloklarını `log.md`'ye taşır, şema sürümünü damgalar. İdempotent. |

### Şablonlar

| Şablon | Kullanım yeri |
|---|---|
| `wiki-CLAUDE.md.tmpl` | Yeni wiki'ye düşürülen şema dosyası |
| `source-summary.md.tmpl` | İçe aktarılan bir kaynak — iddialar, metodoloji, çapraz bağlantılar, açık sorular |
| `entity-page.md.tmpl` | Kişiler, kuruluşlar, yerler, ürünler |
| `concept-page.md.tmpl` | Fikirler, çerçeveler, teoriler, terimler |
| `comparison-page.md.tmpl` | "X vs Y" sayfaları |
| `index.md.tmpl` | İlk içerik kataloğu |
| `log.md.tmpl` | Bootstrap girdisiyle ilk log |
| `hot.md.tmpl` | İlk sıcak önbellek — her içe aktarmadan sonra yeniden yazılır |

### Referans Belgeler

`references/` içinde on bir ayrıntılı iş akışı belgesi:
`philosophy.md` · `architecture.md` · `bootstrap-workflow.md` · `ingest-workflow.md` · `query-workflow.md` · `update-workflow.md` · `lint-workflow.md` · `migrate-workflow.md` · `schema-design-guide.md` · `multi-wiki-routing.md` · `teaching-mode.md`

Skill bunları seçici olarak okur — sizin okumanıza gerek yok. Her mod için LLM'e derinlik sağlamak amacıyla buradalar.

---

## Update Modu

Standart ingest tek bir sayfadaki çelişkileri zaten işler. **Update modu**, yeni bir kaynağın birden fazla sayfada farklı biçimlerde parafraz edilmiş bir iddiayı geçersiz kılması durumu içindir.

```
Senaryo: Smith 2024 analizi, Keys 1980'in yedi ülke çalışmasının verileri seçici kullandığını gösteriyor.
Keys r=0.87 iddiası şu şekillerde geçiyor:
  concepts/saturated-fat.md     → "Keys yedi ülkede r=0.87 buldu"
  entities/ancel-keys.md        → "güçlü korelasyon göstermesiyle ünlü"
  concepts/heart-disease.md     → "Keys'e göre doymuş yağ birincil etken"
  concepts/dietary-policy.md    → "doymuş yağ hipotezi on yıllarca politikayı yönlendirdi"

Update modu:
  1. Semantik tarama — dördünü de bulur (grep bulamaz, LLM bulur)
  2. Kapsam gösterir: "4 sayfa etkilendi. Devam edilsin mi?"
  3. Sayfa başına diff-before-write — her değişiklik için e/h/atla/düzenle
  4. Sayfa başına strateji: revize / disputes / notla (tek tip değil)
  5. Dört düzenlemeyi de Smith 2024'e bağlayan tek log girişi
```

---

## Otomatik Tarihli Lint Raporları

`lint_wiki.py` bayrak olmadan çalıştırıldığında:
- `wiki/reports/lint-YYYY-MM-DD.md` yazar (aynı gün tekrar çalıştırıldığında üzerine yazar — günlük idempotent)
- Otomatik olarak `Reports` indeks girişi ekler
- Otomatik olarak `lint | Sağlık kontrolü` log girişi ekler
- Herhangi bir blok-önem düzeyinde sorun bulunursa kod 1 ile çıkar (CI için kullanışlı)

Override bayrakları: `--stdout` (terminal, takip yok), `--no-track` (dosya yaz, indeks/log atla), `--report PATH` (özel yol).

---

## Çok-Wiki

Çoğu kullanıcı tek bir wiki ile başlar. **İki** wiki'niz olduğunda — örneğin çalışma dizinindeki proje wikisi ve uzun ömürlü global bir "second brain" (çoğu zaman mevcut bir Obsidian vault'u) — skill, yazmaları projenin `CLAUDE.md`'sindeki tek bir tanıma göre ikisi arasında yönlendirir.

```
~/projects/x-project/          ← active project (current working directory)
├── CLAUDE.md                  ← project schema — declares the global wiki path
├── raw/                       ← project sources
└── wiki/                      ← project wiki

~/Documents/obsidian/          ← global wiki (long-lived, exists across projects)
├── CLAUDE.md                  ← global schema
├── raw/
└── wiki/
```

### Tek Seferlik Kurulum

Projenin `CLAUDE.md`'sine şunu ekleyin (ya da agent'tan eklemesini isteyin):

```markdown
## External Wiki

Global knowledge base: ~/Documents/obsidian/

### Routing rules
- Project-specific code decisions, architecture, bugs, configuration → this project's `wiki/`
- Concepts, frameworks, patterns, ideas applicable beyond this project → global wiki
- When in doubt, ask before writing
- Scripts always need `--path` flag pointing to the right wiki root

### Cross-wiki links
- Use absolute paths (`~/...`) when linking from one wiki to the other.
- Never use relative paths that cross wiki boundaries.
```

Yönlendirme kuralları projeye özgü bilgiyi proje wikisine, projeden bağımsız bilgiyi global wikiye gönderir. Wikiler arası bağlantılar her zaman mutlak yolla (`~/...`) verilir; wiki sınırını aşan göreli yol kullanılmaz.

### Dört Temel Senaryo

| # | Senaryo | Tetikleyici | Agent ne yapar |
|---|---|---|---|
| **A** | Projedeyken **global'e yaz** | "JWT refresh rotasyonunu global wiki'me ekle" | Proje `CLAUDE.md`'sini okur → global yolu çözer → global'e yazar, proje wikisine dokunmaz |
| **B** | Global'den **projeye çek** | "Global wiki rate limiting hakkında ne diyor? /api/search'e uygula" | Global sayfaları okur → öneri sentezler → global sayfaya **bağlantı veren** (asla kopyalamayan) projeye özel bir sayfa yazar |
| **C** | Proje sayfasını global'e **taşı** | "concepts/event-sourcing.md olgunlaştı, taşı onu" | İçeriği global'e taşır → proje yolunda tek satırlık yönlendirme bırakır → iki indeksi ve logu günceller |
| **D** | İki wiki'yi **birlikte lint et** | "İki wiki'yi de lint et" | Her birinde `lint_wiki.py --path` çalıştırır → iki raporu okur → tek özet döner |

Dört senaryonun ayrıntılı anlatımı [`references/multi-wiki-routing.md`](references/multi-wiki-routing.md) dosyasında.

---

## Uyumluluk

| Araç | Skills yolu | Notlar |
|---|---|---|
| Claude Code | `~/.claude/skills/` veya `.claude/skills/` | Global veya proje düzeyinde |
| GitHub Copilot (VS Code) | `.vscode/skills/` | Agent modu gerekli |
| OpenAI Codex | `~/.codex/skills/` | Aynı SKILL.md formatı |
| Cursor | `.cursor/skills/` | Proje düzeyinde |
| Gemini CLI | `~/.gemini/skills/` | |

---

## İlgili

- [Karpathy'nin LLM Wiki gist'i](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — orijinal fikir
- [agentskills.io](https://agentskills.io) — açık standart spesifikasyonu

---

## Lisans

MIT — bkz. [LICENSE](LICENSE).
