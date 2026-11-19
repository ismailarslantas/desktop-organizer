<p align="center"><img src="images/01-hero.png" alt="Desktop Organizer by Lionstone" width="100%"></p>

# Masaüstü Düzenleyici — Desktop Organizer by Lionstone

Claude Code ve Codex için taşınabilir bir skill. Windows veya macOS masaüstünüzün kökündeki
dosyaları tek bir **Masaüstü Düzeni** klasöründe 13 kategoriye ayırır. **Hiçbir dosyayı silmez,
üzerine yazmaz, içeriğini değiştirmez; yalnızca taşır.** Taşıma, yazılı planı görüp
**“Planı onaylıyorum”** dedikten ve yalnızca bu bilgisayarda çalışan panoda **Başlat**'a
bastıktan sonra başlar. Her taşıma kayda geçer ve tek komutla geri alınabilir.

[English README](../README.md)

## Kurulum

Gerekli olan tek şey **Python 3.9+**. Skill hiçbir bağımlılığı kendiliğinden kurmaz.

**Claude Code:**

```powershell
git clone https://github.com/ismailarslantas/desktop-organizer.git "$env:USERPROFILE\.claude\skills\desktop-organizer"
```

```bash
git clone https://github.com/ismailarslantas/desktop-organizer.git ~/.claude/skills/desktop-organizer
```

**Codex:**

```powershell
git clone https://github.com/ismailarslantas/desktop-organizer.git "$env:USERPROFILE\.codex\skills\desktop-organizer"
```

```bash
git clone https://github.com/ismailarslantas/desktop-organizer.git ~/.codex/skills/desktop-organizer
```

İkisinde birden tek kopya kullanmak için bir klasöre klonlayıp Windows'ta `mklink /J`, macOS'ta
`ln -s` ile iki konuma bağlayabilirsiniz (ayrıntı İngilizce README'de).

Kurulumdan sonra yeni bir oturumda **“masaüstümü düzenle”** demeniz yeterli. Skill'i kurmak,
dosyaları taşımaya izin vermek anlamına gelmez.

## Akış

1. **Tespit** — gerçek masaüstü işletim sisteminden okunur (OneDrive yönlendirmesi dahil). Ortak
   masaüstüne dokunulmaz. Belirsizlik varsa ajan durup size sorar.
2. **Plan** — yalnızca masaüstünün kökü incelenir. Özet tablo (kategori, dosya sayısı, toplam
   boyut, hedef klasör), ayrıntılı plan (kaynak adı, hedef yol, gerekçe), kopya grupları, isim
   çakışmaları ve atlanan öğeler nedenleriyle gösterilir. Plan benzersiz bir işlem kimliğiyle
   kaydedilir.
3. **Onay** — “Planı onaylıyorum” yazarsınız. Onay yalnızca o plan için geçerlidir; sonradan
   gelen dosyalar dahil edilmez.
4. **Pano** — tarayıcıda `127.0.0.1` üzerinde açılır; onaydan önce Başlat pasiftir. Dosyalar
   anonim renkli kutulardır; ad, yol ve küçük resim gösterilmez. Kutular yaklaşık 50 saniyede
   raflara uçar; taşıması doğrulanmayan kutu rafa inmez. Sağ üstten **TR / EN** dil seçimi yapılır.
5. **Geri alma** — panodaki **Son İşlemi Geri Al** düğmesi ya da tek komut.

## Komutlar

```bash
python scripts/masaustu.py ortam                       # ortam ve masaüstü kontrolü
python scripts/masaustu.py plan                        # planı çıkar ve kaydet
python scripts/masaustu.py onayla <ID> --ifade "Planı onaylıyorum"
python scripts/masaustu.py pano <ID>                   # canlı pano
python scripts/masaustu.py geri-al --son               # son işlemi geri al
python scripts/masaustu.py geri-al <ID>                # belirli işlemi geri al
python scripts/masaustu.py durum                       # işlemler ve kalan dosyalar
python scripts/masaustu.py uzlastir                    # yarım kayıtları dosya durumuyla eşle
```

## Yarım kalan işlem

Bilgisayar kapanırsa, uygulama çökerse ya da ajan bir kullanım limitine takılırsa sorun yok.
`durum` komutu yarım kalan işlemi ve bekleyen dosya sayısını gösterir. Aynı işlem kimliğiyle
panoyu açtığınızda **Kaldığı Yerden Devam Et** düğmesi çıkar: aynı onaylı plan kullanılır, yeni
onay gerekmez, taşınmış dosyalara dokunulmaz ve kalan her dosya taşınmadan önce yeniden denetlenir.

## Güvenlik kuralları (özet)

- Outlook veri dosyaları (`.pst`, `.ost`, `.nst`) asla plana girmez, taşınmaz, ellenmez.
- Klasörler, kısayollar (`.lnk .url .webloc .desktop`), gizli/sistem dosyaları ve bağlantılar
  yerinde kalır. Simge konumları, duvar kâğıdı ve sistem ayarları değişmez.
- Word/Excel/PowerPoint'te açık olan (yanında `~$` kilit dosyası bulunan), son 15 dakikada değişen, yarım inen, kilitli, yalnızca bulutta bulunan veya iki kontrol arasında
  değişen dosyalar atlanır; bulut dosyaları için indirme başlatılmaz.
- Aynı isim varsa uzantı korunarak ` (2)` eklenir. Sürücüler arası kopyala-sil yapılmaz.
- Kopyalar boyut + SHA-256 ile bulunur; en eski değiştirilme zamanlı dosya kendi kategorisinde
  kalır, diğerleri `13_Kopyalar`'a taşınır. Kopyaları taşımak disk alanı kazandırmaz.
- Kayıtlar masaüstünde değil, kullanıcı uygulama verisi klasöründe tutulur
  (`%LOCALAPPDATA%\MasaustuDuzenleyici`, macOS'ta `~/Library/Application Support/MasaustuDuzenleyici`).
- Aynı anda iki düzenleme ya da geri alma yapılamaz.

## Test

```bash
python -m unittest discover -s tests -v
```

Testler geçici bir örnek masaüstünde çalışır; gerçek masaüstünüze dokunmaz. GitHub Actions aynı
testleri Windows, macOS ve Ubuntu üzerinde çalıştırır.
