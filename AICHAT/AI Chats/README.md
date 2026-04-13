# Telegram Manager - Mass Messaging Platform

Django asosidagi Telegram account va mass messaging boshqaruv tizimi. Bir nechta Telegram accountlarini boshqaring, kontaktlarni import qiling va AI yordamida mass messaging amalga oshiring.

## 🚀 Asosiy Imkoniyatlar

### ✅ Account Management
- Bir nechta Telegram accountlarni qo'shish va boshqarish
- Telethon API orqali to'liq integratsiya
- Account holatini real-time monitoring
- Spam detection va avtomatik himoya

### ✅ Mass Messaging
- Bir nechta accountdan bir vaqtda xabar yuborish
- Ko'plab contactlarga parallel xabar yuborish
- AI yordamida har bir contact uchun unique xabar yaratish
- Spam detection va avtomatik to'xtatish
- Campaign statistikasi va progress tracking

### ✅ Contact Management  
- Excel fayllaridan kontaktlarni import qilish
- Telegram bilan sinxronlash
- Telefon raqamlarni tekshirish
- Kontaktlarni account bo'yicha filterlash

### ✅ Chat Interface
- Telegram stilidagi modern chat interface
- Chap tomonda chatlar ro'yxati
- O'ng tomonda xabarlar oynasi
- Real-time xabar yangilanishi
- Account switcher

### ✅ AI Integration
- OpenAI, Claude, Gemini qo'llab-quvvatlash
- Custom promptlar
- Har bir contact uchun personalized xabarlar
- Avtomatik javoblar (kelgusida)

## 📋 Talablar

- Python 3.8+
- Django 5.2.8
- SQLite3 (yoki PostgreSQL)
- Telegram API credentials (api_id va api_hash)

## 🔧 O'rnatish

1. **Repository ni clone qiling:**
```bash
git clone https://gitlab.com/Fatkhiddin/manage-telegram.git
cd manage-telegram
```

2. **Virtual environment yarating:**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. **Dependencies o'rnating:**
```bash
pip install -r requirements.txt
```

4. **Database migrate qiling:**
```bash
python manage.py migrate
```

5. **Superuser yarating:**
```bash
python manage.py createsuperuser
```

6. **Serverni ishga tushiring:**
```bash
python manage.py runserver
```

## 📱 Telegram API Credentials

1. [my.telegram.org](https://my.telegram.org) ga kiring
2. API development tools ga o'ting
3. **api_id** va **api_hash** oling
4. Loyihada account qo'shishda ishlatiladi

## 🎯 Foydalanish

### Account Qo'shish
1. Dashboard → "Yangi Account" tugmasini bosing
2. API credentials va telefon raqamingizni kiriting
3. Telegram dan kelgan kodni kiriting
4. Account faol bo'ladi

### Mass Messaging
1. Dashboard → "Mass Messaging" sahifasiga o'ting
2. Accountlarni tanlang
3. Contactlarni tanlang
4. Xabar yoki AI prompt kiriting
5. "Yuborishni boshlash" tugmasini bosing

### AI Messaging
1. AI Integration sahifasida provider sozlang (OpenAI)
2. API key kiriting
3. Mass messaging da "AI yordamida" checkboxni yoqing
4. Prompt kiriting (masalan: "Foydalanuvchidan qanday uy kerak ekanligini so'rang")
5. AI har bir contact uchun unique xabar yaratadi

## 🛡️ Spam Himoyasi

Tizim avtomatik ravishda:
- FLOOD_WAIT xatoliklarini aniqlaydi
- Spam blocked accountlarni bloklaydi
- Account holatini monitoring qiladi
- Campaign ni to'xtatadi agar spam aniqlansa

## 📊 Arxitektura

```
User
  ├── TelegramAccount (Ko'p accountlar)
  │     ├── Contacts
  │     ├── Chats
  │     └── Messages
  │
  └── MessagingCampaign
        ├── Selected Accounts
        ├── Selected Contacts
        └── CampaignMessageLog
```

## 🔐 Xavfsizlik

⚠️ **Production uchun:**
- `DEBUG = False` qiling
- `SECRET_KEY` ni environment variablelarga o'tkazing
- PostgreSQL yoki boshqa production DBga o'ting
- HTTPS ishlatilsin
- API keylarni himoyalang

## 🤝 Hissa Qo'shish

Pull requestlar qabul qilinadi! Katta o'zgarishlar uchun birinchi issue oching.

## 📝 Litsenziya

[MIT License](LICENSE)

## 👨‍💻 Muallif

**Fatkhiddin**
- GitLab: [@Fatkhiddin](https://gitlab.com/Fatkhiddin)

## 🙏 Minnatdorchilik

- Django framework
- Telethon library
- OpenAI API
- Bootstrap va FontAwesome

---

**Diqqat:** Ushbu loyiha ta'lim maqsadida yaratilgan. Spam yuborish uchun ishlatmang! Telegram qoidalariga rioya qiling.



## Getting started

To make it easy for you to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

- [ ] [Create](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#create-a-file) or [upload](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#upload-a-file) files
- [ ] [Add files using the command line](https://docs.gitlab.com/topics/git/add_files/#add-files-to-a-git-repository) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://gitlab.com/Fatkhiddin/manage-telegram.git
git branch -M main
git push -uf origin main
```

## Integrate with your tools

- [ ] [Set up project integrations](https://gitlab.com/Fatkhiddin/manage-telegram/-/settings/integrations)

## Collaborate with your team

- [ ] [Invite team members and collaborators](https://docs.gitlab.com/ee/user/project/members/)
- [ ] [Create a new merge request](https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html)
- [ ] [Automatically close issues from merge requests](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
- [ ] [Enable merge request approvals](https://docs.gitlab.com/ee/user/project/merge_requests/approvals/)
- [ ] [Set auto-merge](https://docs.gitlab.com/user/project/merge_requests/auto_merge/)

## Test and Deploy

Use the built-in continuous integration in GitLab.

- [ ] [Get started with GitLab CI/CD](https://docs.gitlab.com/ee/ci/quick_start/)
- [ ] [Analyze your code for known vulnerabilities with Static Application Security Testing (SAST)](https://docs.gitlab.com/ee/user/application_security/sast/)
- [ ] [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/ee/topics/autodevops/requirements.html)
- [ ] [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/ee/user/clusters/agent/)
- [ ] [Set up protected environments](https://docs.gitlab.com/ee/ci/environments/protected_environments.html)

***

# Editing this README

When you're ready to make this README your own, just edit this file and use the handy template below (or feel free to structure it however you want - this is just a starting point!). Thanks to [makeareadme.com](https://www.makeareadme.com/) for this template.

## Suggestions for a good README

Every project is different, so consider which of these sections apply to yours. The sections used in the template are suggestions for most open source projects. Also keep in mind that while a README can be too long and detailed, too long is better than too short. If you think your README is too long, consider utilizing another form of documentation rather than cutting out information.

## Name
Choose a self-explaining name for your project.

## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Badges
On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.
