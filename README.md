# 📊 Farol de Clientes

Sistema de análise e monitoramento de engajamento de clientes, com foco em prevenção de churn. Desenvolvido em Flask, permite importar bases de clientes, analisar riscos e acompanhar planos de ação com times de atendimento e sucesso do cliente.

---

## 🚀 Funcionalidades principais

- 🔍 Identificação de clientes em risco de churn
- 🗃️ Importação de bases de clientes e planos
- 📝 Cadastro de comentários e planos de ação
- 📊 Ranking por nível de risco
- 🧠 Visualização de timeline de ações
- 🔐 Área administrativa para gerenciamento

---

## 🖼️ Exemplos visuais

### 📋 Lista de Clientes
Visualização de todos os clientes, com status, CS responsável e ações rápidas:

<img width="2159" height="1113" alt="print_farol_clientes" src="https://github.com/user-attachments/assets/d0f00176-2169-4e63-bf87-40cdea96b1c4" />



---

### 🚦 Ranking de Risco
Clientes ordenados por risco com filtros temporais e exportação de dados:

<img width="2154" height="1041" alt="print_farol_risco" src="https://github.com/user-attachments/assets/5d33e95e-abf2-414e-ae05-d543bd019b0f" />



---

### 🕒 Timeline de Planos
Visualização em linha do tempo dos planos de ação e seus status:

<img width="2162" height="908" alt="print_farol_timeline" src="https://github.com/user-attachments/assets/db4547da-304b-4f2e-8b8e-e1ac69a3941d" />



---

## ⚙️ Tecnologias utilizadas

- Python
- Flask
- Jinja2 (HTML templating)
- Bootstrap (CSS)

---

## 📂 Estrutura de diretórios

```bash
Farol/
├── app.py
├── templates/
│   ├── clientes.html
│   ├── planos_kanban.html
│   ├── planos_timeline.html
│   ├── ranking.html
│   └── ...
├── static/
│   └── ...
└── database/
