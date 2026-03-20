## Regras obrigatórias antes de implementar

- Antes de qualquer implementação, **use o Context7** para procurar **referências de código** na **documentação mais atual**.
- Sempre que possível, **siga a estrutura MVVM pragmática + Coordinator**.
- **Nunca crie módulos “jogados”**: organize tudo corretamente (pastas, nomes, responsabilidades e separação de camadas).

## Classificação arquitetural

- **View / ViewModel (MVVM)**: estado e comportamento da tela, validação local, apresentação e feedback visual. Em **Qt Widgets**, trate MVVM como organização **pragmática** da apresentação, não como modelo “de livro”.
- **Coordinator**: fluxo e ciclo de vida da aplicação: startup, navegação, diálogos, login/logout, restart. **Não** concentra regra de negócio nem processamento técnico.
- **Service (Application)**: coordena caso de uso, etapas e dependências sem conhecer detalhes visuais. **Service coordena; Core executa**.
- **Domain**: entidades, value objects, invariantes, enums e contratos estáveis do negócio, sem dependência de framework.
- **Core**: processamento técnico/algorítmico, workers, pipelines, motores internos e execução concorrente. **Não** depende de UI.
- **Infrastructure**: adapta Qt, SDKs, rede, storage, filesystem e demais dependências externas; implementa contratos internos e traduz modelos externos.
- **app/**: composition root, bootstrap e wiring entre Coordinator, Services, Infrastructure, ViewModels e Views.

## Dependências e tipos

- As dependências devem apontar **de fora para dentro**.
- **UI** e **app/** ficam na borda; **Infrastructure** implementa contratos internos; **Service (Application)** pode depender de **Domain** e colaborar com **Core**; **Domain** não depende de camadas externas.
- **DTOs / Commands / Queries / Results** de caso de uso tendem a ficar em **Service (Application)**.
- **Modelos e contratos estáveis do negócio** tendem a ficar em **Domain**.
- **Tipos técnicos internos** tendem a ficar em **Core**.
- **Tipos de framework, API, SDK ou formatos externos** tendem a ficar em **Infrastructure**.
- **Modelos de apresentação e estado de tela** tendem a ficar em **ViewModel**.

## Regras de corte

- **View** não cria `Service` nem `Coordinator` diretamente; a composição acontece em `src/app/`.
- **View** não acessa filesystem, rede, worker ou regra de negócio diretamente.
- **ViewModel** não vira dono do fluxo global; quando isso acontecer, extraia para **Coordinator**.
- **Coordinator** reage aos resultados de `Services` / `ViewModels` para definir fluxo; ele **não** decide regra de negócio.
- **Service** não depende de `QWidget`, `QMainWindow`, diálogos ou detalhes visuais, e não deve virar motor técnico interno.
- **Domain** não depende de Qt, UI, storage, rede ou filesystem.
- **Infrastructure** não incorpora regra de negócio só porque usa biblioteca externa.
- **app/** não contém lógica de negócio.
- **Core** não monta mensagem final para o usuário; ele retorna dados estruturados para a apresentação formatar.

## Exceções e regra de ouro

- Em fluxos pequenos, uma classe pode acumular responsabilidade **temporariamente**, desde que isso seja explícito, local e com intenção clara de extração futura.
- Exceções pontuais não redefinem a regra arquitetural do projeto.
- Se uma classe mistura **estado de tela**, **fluxo**, **caso de uso**, **regra de negócio**, **processamento técnico** ou **adaptação de framework**, ela está acumulando responsabilidades e deve ser dividida.
- Em caso de dúvida, classifique pela **responsabilidade dominante** e extraia o restante para colaboradores menores.
