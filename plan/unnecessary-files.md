# সম্ভাব্য অপ্রয়োজনীয় ফাইল — যাচাই তালিকা

> এটি deletion নির্দেশ নয়। শুধু বর্তমান working tree, Git index ও source reference দেখে শ্রেণিবিন্যাস। কোনো ফাইল সরানো হয়নি। বিশেষত `py/` এবং `g2.spec` ইতোমধ্যে **tracked deletion** অবস্থায় আছে; এগুলোর অবস্থা কেন বদলেছে নিশ্চিত না করে commit/restore করবেন না।

## উচ্চ আস্থা — নতুন API/Compose-এর জন্য প্রয়োজন নেই, তবু পুরোনো workflow পরীক্ষা করতে হবে

| ফাইল/গ্রুপ | প্রমাণ | প্রস্তাবিত সিদ্ধান্ত |
| --- | --- | --- |
| `ps_lib/requests-html.py` | ০ বাইট; tracked, কোনো ব্যবহার পাওয়া যায়নি। | পুরোনো workflow-তেও প্রয়োজন না থাকলে মুছতে পারেন। |
| `.dockerenv` | ০ বাইট marker; Dockerfile/Compose-এ কোনো reference নেই। | ব্যবহারের কারণ না থাকলে বাদ। |
| `py/chromedriver` | Git blob `chromedriver`-এর সঙ্গে হুবহু একই (~১৪ MB); `py/` কপি এখন working tree-তে নেই। | নতুন Remote WebDriver-এর জন্য দুই কপির কোনোটিই দরকার নেই; legacy ব্যবহারের সিদ্ধান্ত নিয়ে পরে সরান। |
| `py/ps_lib/`-এর ১৪টি অভিন্ন কপি | Git blob তুলনায় root `ps_lib/`-এর সঙ্গে হুবহু এক: `accounts.py`, `captcha.py`, `helper.py`, `imap.py`, `imap_all_server.py`, `jsbrowser.py`, `lang.py`, `loction.py`, `post.py`, `proxy.py`, `psThread.py`, `ps_str.py`, `timezone.py`, `userAgent.py`। বর্তমানে সব deleted। | `py/` থেকে কোনো পৃথক launcher না থাকলে root কপি রেখে duplicate বাদ; আগে dependency যাচাই। |

## সম্ভাব্য অব্যবহৃত/উৎপন্ন — উদ্দেশ্য নিশ্চিত করে তবেই সরাবেন

| ফাইল/গ্রুপ | দেখা গেছে | কেন সিদ্ধান্ত বাকি |
| --- | --- | --- |
| `9016506343-match-type-1.png`, `9016506542-match-type-1.png`, `9016506595-match-type-1.png`; `img/9016505552.png`–`img/9016505557.png` | tracked screenshot/ছবি; source-এ এই নির্দিষ্ট নামের reference পাওয়া যায়নি। | Debug artifact না প্রয়োজনীয় sample/test fixture, মালিকের কাছে নিশ্চিত করা দরকার; ছবিতে ব্যক্তিগত তথ্য থাকতে পারে। |
| `data/nowsecure.png`, `img/nowsecure.png` | একই নাম, কিন্তু file hash **আলাদা**; code reference পাওয়া যায়নি। | আলাদা design/asset হতে পারে; content দেখে নিশ্চিত করুন, duplicate ধরে delete নয়। |
| `Untitled-1.ipynb` | ছোট ad-hoc notebook; `pyautogui` import, app integration পাওয়া যায়নি। | গবেষণা নোট দরকার থাকলে archive; নয়তো অপসারণ। |
| `info.txt` | app setup-এ reference পাওয়া যায়নি। | পড়ে উদ্দেশ্য/সংবেদনশীলতা নিশ্চিত করে archive/delete (এখানে content প্রকাশ করা হয়নি)। |
| `setup.sh`, `down.sh`, `supervisord.conf`, `monitor.py` | legacy install/supervisor/docker worker উপাদান; বর্তমান Dockerfile-এর supervisor command comment করা; নতুন Compose API এগুলো ব্যবহার করবে না। | পুরোনো deployment চালু থাকলে কার্যকর হতে পারে; নতুন pipeline সফল হলে deprecate/সরান। |
| `g2.spec`, `py/g2.spec` | PyInstaller spec; root `g2.spec` ও `py/g2.spec` বর্তমানে tracked deletion। | standalone binary build দরকার কি না নিশ্চিত করুন। |
| `ps_lib/jsbrowser.py`, `ps_lib/firefox.py`, `ps_lib/imap_all_server.py`, `ps_lib/lang.py` | নতুন headless Chrome Remote tool-এর প্রয়োজন নেই; `jsbrowser.py`-এ PhantomJS ব্যবহার আছে। | legacy import/বাইরের ব্যবহার সম্পূর্ণ যাচাই ছাড়া মুছবেন না। |
| `ps_lib/GCW.py` বনাম `GCW.py` | দুটি আলাদা worker variant, hash আলাদা; একটিকে অন্যটির exact copy বলা যায় না। | কোনটি ব্যবহার হয় নিশ্চিত করে আলাদা refactor সিদ্ধান্ত। |
| `chromedriver` | tracked binary (~১৪ MB); নতুন Selenium Standalone-এ browser container নিজের driver দেবে। | legacy local-browser launch `ps_lib/browser.py`-তে driver path ব্যবহার করে; legacy retire না করে বাদ নয়। |

## যে deleted ফাইলগুলোকে সরাসরি 'অপ্রয়োজনীয়' বলা যাচ্ছে না

`py/GCW.py`, `py/g2.py`, `py/g2orginal.py`, `py/monitor.py`, `py/r3c.py`, `py/ps_lib/ps_setup.py`, `py/ps_lib/uc.py`, `py/ps_lib/-- SQLite.sql` এবং root `g2.spec`—কিছুতে মূল কপি থেকে ভিন্ন code/schema আছে, কিছুতে কোনো root counterpart নেই। এই তালিকা **restore-ও নয়, cleanup approval-ও নয়**। মুছে যাওয়া ২৫টি tracked file-এর পূর্ণ তালিকা `git ls-files -d` দিয়ে যাচাই করুন।

## ফাইল নয়, কিন্তু জরুরি ignore/security housekeeping

- `.env` untracked হলেও `.gitignore`/`.dockerignore`-এ বাদ দেওয়া নেই। এটি কখনও Git-এ stage বা image-এ COPY করবেন না; পরবর্তী বাস্তবায়নে দুই ignore file-এ সংশোধন এবং `.env.example`।
- `.claude/` untracked; project-local tool/worktree data। build context থেকে বাদ দিন; এর ভেতরের worktree ব্যবহার/পুনরুদ্ধারের সিদ্ধান্ত আলাদা।
- `.dockerignore`-এর `.db`, `.html`, `.spec` pattern-গুলো যথাক্রমে `*.db`, `*.html`, `*.spec`-এর মতো glob নয়; build context exclusion যাচাই করা দরকার।
- `ps_lib/ps_setup.py` এবং `monitor.py`-এ source-এ সরাসরি credentials/keys আছে; এই তালিকায় মান প্রকাশ করা হয়নি। যথাযথ অনুমতি নিয়ে rotate, config-এ সরানো এবং Git history exposure মূল্যায়ন করুন।
