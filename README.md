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

<img width="2159" height="1113" alt="print_farol_clientes" src="https://github.com/user-attachments/assets/0fa14380-5e14-4dc6-9e42-dbfe13f5c48e" />


---

### 🚦 Ranking de Risco
Clientes ordenados por risco com filtros temporais e exportação de dados:

<img width="2154" height="1041" alt="print_farol_risco" src="https://github.com/user-attachments/assets/a85c1f14-35f2-43ac-82b2-47a73a8a9794" />


---

### 🕒 Timeline de Planos
Visualização em linha do tempo dos planos de ação e seus status:

<img width="2162" height="908" alt="print_farol_timeline" src="https://github.com/user-attachments/assets/d54b6713-78af-489e-8c1a-c69e0cd8efd8" />


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
