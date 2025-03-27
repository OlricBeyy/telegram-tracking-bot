# Railway Deployment Guide for Telegram Bot

Bu rehber Telegram botunuzu Railway.app platformuna nasıl yükleyeceğinizi adım adım açıklar.

## 1. Railway.app Hesabı Oluşturma

1. [Railway.app](https://railway.app/) adresine gidin
2. "Login" butonuna tıklayın
3. GitHub hesabınızla giriş yapın (GitHub hesabınız yoksa önce bir tane oluşturun)
4. İlk kez kullanıyorsanız, Railway size ücretsiz bir kredi ($5) verecektir

## 2. Projeyi GitHub'a Yükleme

1. [GitHub](https://github.com/) adresinde yeni bir repository oluşturun
2. Aşağıdaki komutları kullanarak projemizi bu repo'ya yükleyin:

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/KULLANICI_ADINIZ/REPO_ADINIZ.git
git push -u origin main
```

## 3. Gerekli Railway Yapılandırma Dosyaları

### Procfile Oluşturma

Railway'de, uygulamanızın nasıl başlatılacağını belirten bir `Procfile` dosyası oluşturun:

```
web: gunicorn --bind 0.0.0.0:$PORT main:app
worker: python run_bot.py
```

Bu dosya, web sunucusu (keep-alive için) ve Telegram bot işlemini başlatır.

### requirements.txt Dosyası

Railway, bu dosyayı kullanarak gerekli Python paketlerini otomatik olarak yükler:

```
beautifulsoup4==4.12.2
email-validator==2.1.0.post1
flask==2.3.3
flask-sqlalchemy==3.1.1
gunicorn==21.2.0
psycopg2-binary==2.9.9
python-telegram-bot==13.15
requests==2.31.0
telegram==0.0.1
trafilatura==1.6.2
```

## 4. Railway'de Yeni Proje Oluşturma

1. Railway dashabord'da "New Project" butonuna tıklayın
2. "Deploy from GitHub repo" seçeneğini seçin
3. GitHub hesabınıza erişim için izin verin
4. Projenizi içeren repo'yu seçin
5. Railway otomatik olarak projenizdeki `Procfile` ve `requirements.txt` dosyalarını algılayacak ve kurulumu başlatacaktır

## 5. PostgreSQL Veritabanı Ekleme

1. Railway projenizde, "New" butonuna tıklayın
2. "Database" seçeneğinden "PostgreSQL" seçin
3. Railway otomatik olarak bir PostgreSQL veritabanı oluşturacak

## 6. Çevre Değişkenlerini (Environment Variables) Ayarlama

1. Projenizdeki "Variables" sekmesine tıklayın
2. Aşağıdaki çevre değişkenlerini ekleyin:
   - `TELEGRAM_TOKEN`: Telegram botunuzun token'ı
   - `ADMIN_USER_ID`: Admin kullanıcı ID'niz
   - `DATABASE_URL`: Railway otomatik olarak ekleyecektir, değiştirmeyin

## 7. Deployment'i Başlatma

1. Railway otomatik olarak her GitHub push'unuzdan sonra deployment'ı başlatır
2. Deployment'in durumunu "Deployments" sekmesinden takip edebilirsiniz
3. Deployment tamamlandığında, botunuz çalışmaya başlayacaktır

## 8. Domain ve Monitoring

1. "Settings" sekmesinden projenize özel domain'i görebilirsiniz (web arayüzü için)
2. "Metrics" sekmesinden kaynak kullanımını izleyebilirsiniz

## 9. Aylık Maliyet Yönetimi

1. Railway'in fiyatlandırması kullanım bazlıdır
2. Botunuz genellikle ayda $5-10 arası bir maliyete sahip olacaktır
3. Maliyeti düşük tutmak için:
   - `PRODUCT_CHECK_INTERVAL_MINUTES` değerini artırın (daha az sık kontrol)
   - İhtiyaç olmayan web süreçlerini kapatın

## 10. Sorun Giderme

1. Logları "Deployments" > (en son deployment) > "Logs" sekmesinden görebilirsiniz
2. Herhangi bir hata durumunda, bu logları kontrol edin
3. Veritabanı bağlantı hatası için `DATABASE_URL` değişkenini kontrol edin
4. Bot yanıt vermiyorsa, `TELEGRAM_TOKEN` değerinin doğru olduğundan emin olun

---

Bu rehberi takip ederek Telegram botunuzu Railway.app platformuna başarıyla deploy edebilirsiniz. Railway, otomatik scaling ve 7/24 çalışma sağlayarak botunuzun kesintisiz çalışmasını sağlar.