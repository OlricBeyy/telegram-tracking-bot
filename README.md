# Ürün Takip Telegram Botu

Bu bot, Türk e-ticaret sitelerindeki ürünlerin stok ve fiyat bilgilerini takip etmenize olanak sağlar.

## Özellikler

- Ürün fiyat ve stok takibi
- Fiyat değişikliklerinde bildirim alın
- Ürün tekrar stokta olduğunda bildirim alın
- Kolay kullanıcı arayüzü
- 24/7 kesintisiz çalışma
- Otomatik ürün kontrolü (30 dakikada bir)

## Desteklenen E-Ticaret Siteleri

- Trendyol
- Hepsiburada
- N11
- Amazon (TR)
- Teknosa
- MediaMarkt

## Komutlar

- `/start` - Botu başlatır ve size bir karşılama mesajı gösterir
- `/help` - Yardım mesajını görüntüler
- `/track` - Yeni bir ürün takip etmeye başlar
- `/list` - Takip ettiğiniz ürünleri listeler
- `/reboot` - Botu yeniden başlatır (sorun yaşadığınızda kullanın)

## Teknik Bilgiler

### Sistem Gereksinimleri

- Python 3.9+
- python-telegram-bot v13.15
- PostgreSQL veritabanı
- BeautifulSoup4, Requests kütüphaneleri

### Kurulum

1. Repoyu klonlayın
2. Gerekli paketleri yükleyin: `pip install -r requirements.txt`
3. PostgreSQL veritabanını kurun ve bağlantı bilgilerini `.env` dosyasına ekleyin
4. `.env` dosyasına Telegram bot token'ınızı ekleyin
5. `python run_bot.py` komutu ile botu çalıştırın

### Önemli Çevre Değişkenleri

- `TELEGRAM_TOKEN` - Telegram bot token'ı
- `DATABASE_URL` - PostgreSQL veritabanı bağlantı URL'si

## Nasıl Kullanılır

1. Telegram'da botu başlatın (`/start`)
2. `/track` komutunu kullanarak takip etmek istediğiniz ürünü ekleyin
3. E-ticaret sitesini seçin
4. Ürün URL'sini girin
5. Onaylayın ve işlem tamam!

## Notlar

- Bot, 24/7 çalışacak şekilde optimize edilmiştir
- Veritabanı bağlantısı için PostgreSQL kullanılmaktadır
- Herhangi bir sorun yaşarsanız, `/reboot` komutunu kullanarak botu yeniden başlatabilirsiniz

## İletişim

Sorunlar, öneriler veya geri bildirimler için lütfen GitHub üzerinden bir issue açın.