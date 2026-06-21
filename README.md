# 🤖 Bot de Trading XTB — Benjamin

Bot automatique de trading Forex + Or sur XTB via XAPI.
Stratégie : EMA Crossover + RSI | Instruments : EURUSD, XAUUSD

---

## ⚡ ÉTAPE 1 — Activer les notifications WhatsApp (CallMeBot)

1. Ajoute ce numéro dans tes contacts WhatsApp : **+34 644 69 68 83**
2. Envoie-lui ce message exactement :
   ```
   I allow callmebot to send me messages
   ```
3. Tu reçois en réponse une **clé API** (ex: `1234567`)
4. Note cette clé → tu en auras besoin à l'étape 3

---

## ⚡ ÉTAPE 2 — Pousser le code sur GitHub

```bash
git init
git add .
git commit -m "Bot trading XTB initial"
git branch -M main
git remote add origin https://github.com/TON_USERNAME/xtb-trading-bot.git
git push -u origin main
```

---

## ⚡ ÉTAPE 3 — Déployer sur Railway

1. Va sur [railway.app](https://railway.app)
2. Clique **New Project → Deploy from GitHub repo**
3. Sélectionne `xtb-trading-bot`
4. Va dans **Variables** et ajoute exactement ces 5 variables :

| Variable     | Valeur                        |
|--------------|-------------------------------|
| XTB_LOGIN    | ton email ou numéro XTB       |
| XTB_PASSWORD | ton mot de passe XTB          |
| XTB_TYPE     | real                          |
| WA_PHONE     | 237692497780                  |
| WA_APIKEY    | la clé reçue à l'étape 1     |

5. Clique **Deploy** → le bot démarre !

---

## 📊 Stratégie

| Paramètre    | Valeur          |
|--------------|-----------------|
| Instruments  | EURUSD, XAUUSD  |
| Timeframe    | 5 minutes       |
| EMA rapide   | 5 périodes      |
| EMA lente    | 20 périodes     |
| RSI          | 14 périodes     |
| Stop Loss    | 15 pips         |
| Take Profit  | 30 pips (1:2)   |
| Lot size     | 0.01 (minimum)  |

---

## 📱 Notifications reçues sur WhatsApp

- ✅ Démarrage du bot
- 🟢 BUY ouvert (symbole, prix, SL, TP)
- 🔴 SELL ouvert (symbole, prix, SL, TP)
- ⚠️ Erreurs et reconnexions
