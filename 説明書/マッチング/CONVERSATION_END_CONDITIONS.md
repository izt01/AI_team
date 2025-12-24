# 🎯 進化型システムの会話終了条件 - 完全解説

---

## ❓ あなたの疑問

```
進化型システムは全候補を保持して再評価しているなら、
「3件以下」のような明確な終了条件がないのでは？

既存システム: 3件以下になったら終了
進化型システム: ???
```

### 📌 **素晴らしい指摘です！**

確かに、既存システムのような「件数ベースの終了条件」は使えません。
では、**どうやって会話を終了するのか？**

---

# 1. 進化型システムの終了条件（複数条件の組み合わせ）

## 1-1. 終了判定の設計思想

```
既存システム:
└ シンプルな閾値（3件以下）

進化型システム:
└ 複数の指標を総合的に判断
  ├ 会話の深さ（ターン数）
  ├ 情報の充足度
  ├ スコアの収束度
  ├ ユーザーの満足度推定
  └ 推薦の信頼度
```

---

## 1-2. 具体的な終了条件（5つ）

### 条件1: 会話の深さ（最低ターン数）

```python
MIN_CONVERSATION_DEPTH = 5  # 最低5往復

if conversation_turns >= MIN_CONVERSATION_DEPTH:
    # 最低限の情報は集まった
    can_recommend = True
```

**理由:**
- 少なくとも5回の質疑応答で基本的な希望を把握
- あまりに早く終了すると情報不足

---

### 条件2: 情報の充足度（プロファイル完成度）

```python
def calculate_profile_completeness(user_profile):
    """
    ユーザープロファイルの充足度を計算（0-100%）
    """
    
    required_fields = {
        # 必須情報（各10点）
        'job_title': 10,
        'location': 10,
        'salary_min': 10,
        
        # 重要情報（各8点）
        'work_life_balance_priority': 8,
        'career_growth_priority': 8,
        'career_goal': 8,
        
        # 補足情報（各6点）
        'learning_interests': 6,
        'company_size_preference': 6,
        'remote_preference': 6,
        
        # 詳細情報（各4点）
        'tech_stack_preference': 4,
        'team_preference': 4,
        'work_style_preference': 4,
        'pain_points': 4,
        'decision_style': 4
    }
    
    score = 0
    for field, points in required_fields.items():
        if user_profile.get(field):
            score += points
    
    return score  # 0-100

# 終了条件
if calculate_profile_completeness(user_profile) >= 70:
    # 70%以上の情報が揃った
    can_recommend = True
```

**例:**
```
会話1回目: 30%（基本情報のみ）
会話2回目: 45%（優先度追加）
会話3回目: 60%（キャリア目標追加）
会話4回目: 75%（詳細な希望追加）← 終了条件クリア！
```

---

### 条件3: スコアの収束度（上位候補の安定性）

```python
def calculate_score_convergence(score_history):
    """
    スコアが収束しているか判定
    
    過去3回の質問で上位候補の順位が安定していれば
    これ以上質問しても変わらない可能性が高い
    """
    
    if len(score_history) < 3:
        return False
    
    # 過去3回の上位5件を比較
    recent_top5 = [
        set(iteration['top5_job_ids']) 
        for iteration in score_history[-3:]
    ]
    
    # 3回連続で上位5件の80%以上が同じなら収束
    intersection = recent_top5[0] & recent_top5[1] & recent_top5[2]
    
    if len(intersection) >= 4:  # 5件中4件が同じ
        return True
    
    return False

# 終了条件
if calculate_score_convergence(conversation_history):
    # スコアが安定してきた
    can_recommend = True
```

**例:**
```
質問1後の上位5件: [A, B, C, D, E]
質問2後の上位5件: [A, C, B, F, D]  ← まだ変動
質問3後の上位5件: [A, C, B, D, F]  ← まだ変動
質問4後の上位5件: [A, C, B, D, G]  ← A, C, B, D が安定
質問5後の上位5件: [A, C, B, D, H]  ← A, C, B, D が安定
                                      ↑ 収束！終了条件クリア
```

---

### 条件4: 推薦の信頼度（十分なマッチング精度）

```python
def calculate_recommendation_confidence(top_candidates):
    """
    推薦の信頼度を計算
    
    上位候補のスコアが十分に高く、
    かつ差が明確なら信頼できる推薦
    """
    
    if not top_candidates:
        return 0.0
    
    top1_score = top_candidates[0]['final_score']
    top5_avg = sum(c['final_score'] for c in top_candidates[:5]) / 5
    
    # 条件1: トップスコアが80点以上
    if top1_score < 80:
        return 0.5  # 低信頼度
    
    # 条件2: 上位5件の平均も70点以上
    if top5_avg < 70:
        return 0.6  # やや低信頼度
    
    # 条件3: 1位と2位の差が5点以上（明確な差）
    if len(top_candidates) > 1:
        score_gap = top1_score - top_candidates[1]['final_score']
        if score_gap < 5:
            return 0.7  # 中信頼度（差が小さい）
    
    return 0.9  # 高信頼度

# 終了条件
if calculate_recommendation_confidence(candidates) >= 0.8:
    # 信頼できる推薦ができる
    can_recommend = True
```

**例:**
```
会話3回目:
- 1位: 68点
- 2位: 67点
→ 信頼度: 0.5（スコア低い、差が小さい）
→ まだ続行

会話5回目:
- 1位: 85点
- 2位: 78点
- 3-5位平均: 73点
→ 信頼度: 0.9（スコア高い、明確な差）
→ 終了条件クリア！
```

---

### 条件5: ユーザーの満足度推定（早期終了の検出）

```python
def estimate_user_satisfaction(user_messages):
    """
    ユーザーの発言からAIで満足度を推定
    
    ユーザーが「もう十分」「これで決めたい」などの
    サインを出していないか検出
    """
    
    recent_messages = user_messages[-3:]
    
    # AIで分析
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "system",
            "content": """
ユーザーの最近の発言から満足度を推定してください。

以下の場合は早期終了シグナル:
- 「もう十分です」「これで決めたい」
- 「早く求人を見たい」
- 短い返答が続く（疲れている）
- 「とりあえず見せて」

JSON形式で返してください:
{
  "satisfaction_level": "high" | "medium" | "low",
  "early_exit_signal": true | false,
  "reasoning": "理由"
}
"""
        }, {
            "role": "user",
            "content": json.dumps(recent_messages)
        }],
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    return result

# 終了条件
user_state = estimate_user_satisfaction(messages)
if user_state['early_exit_signal']:
    # ユーザーが早期終了を望んでいる
    can_recommend = True
```

**例:**
```
ユーザー発言:
会話3回目: 「リモートワークを希望します。通勤が...（詳細）」
会話4回目: 「家族との時間を大切にしたいです...（詳細）」
→ 満足度: 高い（積極的に話している）
→ 続行

会話5回目: 「はい」
会話6回目: 「まあまあ」
会話7回目: 「早く求人を見たいです」
→ 満足度: 低下、早期終了シグナル
→ 終了条件クリア
```

---

## 1-3. 総合判定ロジック

```python
class ConversationEndController:
    """
    会話終了の総合判定
    """
    
    def should_end_conversation(self, context):
        """
        複数の条件を総合的に判断
        """
        
        # 各条件をチェック
        checks = {
            'min_turns': context['conversation_turns'] >= 5,
            'profile_complete': context['profile_completeness'] >= 70,
            'score_converged': context['score_convergence'],
            'high_confidence': context['recommendation_confidence'] >= 0.8,
            'user_satisfied': context['user_satisfaction']['early_exit_signal']
        }
        
        # 終了パターンの定義
        
        # パターン1: 理想的な終了（すべて満たす）
        if all(checks.values()):
            return {
                'should_end': True,
                'reason': 'ideal_completion',
                'message': '十分な情報が集まりました。最適な求人をご提案します！'
            }
        
        # パターン2: 十分な情報が集まった（主要条件クリア）
        if (checks['min_turns'] and 
            checks['profile_complete'] and 
            checks['high_confidence']):
            return {
                'should_end': True,
                'reason': 'sufficient_information',
                'message': '素晴らしい！あなたに最適な求人が見つかりました。'
            }
        
        # パターン3: スコア収束（これ以上質問しても変わらない）
        if (checks['min_turns'] and 
            checks['score_converged'] and 
            checks['profile_completeness'] >= 60):
            return {
                'should_end': True,
                'reason': 'score_stabilized',
                'message': 'おすすめの求人が絞り込めました。ご覧ください。'
            }
        
        # パターン4: ユーザーの早期終了希望
        if checks['user_satisfied']:
            return {
                'should_end': True,
                'reason': 'user_requested',
                'message': 'かしこまりました。現時点でのおすすめをご紹介します。'
            }
        
        # パターン5: 最大ターン数に達した（安全装置）
        if context['conversation_turns'] >= 10:
            return {
                'should_end': True,
                'reason': 'max_turns_reached',
                'message': '詳しくお聞きできました。厳選した求人をご紹介します。'
            }
        
        # まだ続行
        return {
            'should_end': False,
            'reason': 'needs_more_information',
            'next_question': self.generate_next_question(context)
        }


# 使用例
controller = ConversationEndController()

# 毎回の会話後に判定
context = {
    'conversation_turns': 5,
    'profile_completeness': 75,
    'score_convergence': True,
    'recommendation_confidence': 0.85,
    'user_satisfaction': {'early_exit_signal': False}
}

decision = controller.should_end_conversation(context)

if decision['should_end']:
    print(decision['message'])
    show_recommendations()
else:
    ask_next_question(decision['next_question'])
```

---

# 2. 実際の会話フロー例

## 2-1. 正常な終了パターン

```
【ユーザー: デザイナー志望、東京都】

┌─────────────────────────────────────┐
│ 会話1回目                            │
├─────────────────────────────────────┤
│ AI: 「理想の働き方を教えてください」│
│ User: 「リモートワーク希望。通勤... │
│       が長くて家族時間が...」       │
│                                     │
│ [判定]                              │
│ - ターン数: 1/5 ❌                  │
│ - 充足度: 30% ❌                    │
│ - 収束度: なし ❌                   │
│ - 信頼度: 0.4 ❌                    │
│ → 続行                              │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 会話2回目                            │
├─────────────────────────────────────┤
│ AI: 「その時間を何に使いたい？」    │
│ User: 「家族時間とReact勉強」       │
│                                     │
│ [判定]                              │
│ - ターン数: 2/5 ❌                  │
│ - 充足度: 45% ❌                    │
│ - 収束度: なし ❌                   │
│ - 信頼度: 0.5 ❌                    │
│ → 続行                              │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 会話3回目                            │
├─────────────────────────────────────┤
│ AI: 「Reactは将来のため？」         │
│ User: 「フロントエンドスペシャリ... │
│       ストが目標です」              │
│                                     │
│ [判定]                              │
│ - ターン数: 3/5 ❌                  │
│ - 充足度: 60% ❌                    │
│ - 収束度: なし ❌                   │
│ - 信頼度: 0.6 ❌                    │
│ → 続行                              │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 会話4回目                            │
├─────────────────────────────────────┤
│ AI: 「A, B, Cならどれを選ぶ？」     │
│ User: 「Bです。メンターが重要」     │
│                                     │
│ [判定]                              │
│ - ターン数: 4/5 ❌                  │
│ - 充足度: 72% ✅                    │
│ - 収束度: まだ変動 ❌               │
│ - 信頼度: 0.75 ❌                   │
│ → 続行（もう少し）                  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 会話5回目                            │
├─────────────────────────────────────┤
│ AI: 「チームの雰囲気は重視する？」  │
│ User: 「フラットな組織がいいです」  │
│                                     │
│ [判定]                              │
│ - ターン数: 5/5 ✅                  │
│ - 充足度: 78% ✅                    │
│ - 収束度: 上位4件が安定 ✅          │
│ - 信頼度: 0.88 ✅                   │
│ - ユーザー満足度: 高い ✅           │
│ → 終了！ 🎉                         │
└─────────────────────────────────────┘

AI: 「素晴らしい！あなたに最適な求人が見つかりました。
     
     整理すると:
     ✅ リモートワーク（週3日以上）
     ✅ メンターから学べる環境
     ✅ React/フロントエンド技術
     ✅ フラットな組織
     ✅ 家族との時間確保
     
     この条件で5件の求人を厳選しました。」

[求人リスト表示]
```

---

## 2-2. 早期終了パターン（ユーザーの要望）

```
┌─────────────────────────────────────┐
│ 会話1回目                            │
├─────────────────────────────────────┤
│ AI: 「理想の働き方は？」            │
│ User: 「リモートワーク希望」        │
│                                     │
│ [判定] → 続行                       │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 会話2回目                            │
├─────────────────────────────────────┤
│ AI: 「その理由は？」                │
│ User: 「通勤時間が長い」            │
│                                     │
│ [判定] → 続行                       │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 会話3回目                            │
├─────────────────────────────────────┤
│ AI: 「その時間を何に使いたい？」    │
│ User: 「とりあえず求人を見せて」    │← 早期終了シグナル
│                                     │
│ [判定]                              │
│ - ターン数: 3/5 ❌                  │
│ - 充足度: 50% ❌                    │
│ - ユーザー満足度: 早期終了希望 ✅   │
│ → 早期終了 ⚡                       │
└─────────────────────────────────────┘

AI: 「かしこまりました。
     現時点での情報でおすすめをご紹介します。
     
     もし他にも希望があれば、
     いつでも追加で絞り込めますので
     お気軽にお申し付けください。」

[求人リスト表示]
```

---

## 2-3. スコア収束パターン

```
┌─────────────────────────────────────┐
│ 会話5回目                            │
├─────────────────────────────────────┤
│ 上位5件: [A, C, B, D, E]            │
│ 1位: 85点                           │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 会話6回目                            │
├─────────────────────────────────────┤
│ 上位5件: [A, C, B, D, F]            │
│ 1位: 87点（+2点）                   │
│ → 4件が同じ                         │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 会話7回目                            │
├─────────────────────────────────────┤
│ 上位5件: [A, C, B, D, G]            │
│ 1位: 88点（+1点）                   │
│ → 4件が同じ、スコア微増             │
│                                     │
│ [判定]                              │
│ - ターン数: 7/5 ✅                  │
│ - 充足度: 72% ✅                    │
│ - 収束度: 3回連続で上位4件同じ ✅   │
│ - 信頼度: 0.82 ✅                   │
│ → 収束終了 🎯                       │
└─────────────────────────────────────┘

AI: 「おすすめの求人が絞り込めました。
     これ以上質問を続けても
     大きな変化はなさそうです。
     
     自信を持っておすすめできる5件を
     ご紹介します。」

[求人リスト表示]
```

---

# 3. 既存システムとの比較表

```
┌──────────────┬────────────────┬──────────────────────┐
│ 項目         │ 既存システム    │ 進化型システム        │
├──────────────┼────────────────┼──────────────────────┤
│ 終了条件     │ 候補3件以下    │ 複数条件の総合判断    │
│              │ （単純明快）    │ （柔軟・賢い）        │
├──────────────┼────────────────┼──────────────────────┤
│ 判定方法     │ IF文1つ        │ 5つの条件を評価       │
│              │ if count<=3    │ - ターン数            │
│              │                │ - 充足度              │
│              │                │ - 収束度              │
│              │                │ - 信頼度              │
│              │                │ - ユーザー満足度      │
├──────────────┼────────────────┼──────────────────────┤
│ 最短終了     │ 3回            │ 5回（最低保証）       │
├──────────────┼────────────────┼──────────────────────┤
│ 平均終了     │ 4-5回          │ 6-7回                 │
├──────────────┼────────────────┼──────────────────────┤
│ 最長終了     │ 制限なし       │ 10回（安全装置）      │
├──────────────┼────────────────┼──────────────────────┤
│ 早期終了対応 │ なし           │ ユーザーシグナル検出  │
├──────────────┼────────────────┼──────────────────────┤
│ 柔軟性       │ 低い           │ 高い                  │
├──────────────┼────────────────┼──────────────────────┤
│ 精度         │ 低〜中         │ 高                    │
└──────────────┴────────────────┴──────────────────────┘
```

---

# 4. 実装コード例

```python
# ============================================
# 進化型システムの会話制御
# ============================================

@app.post("/chat")
async def chat_advanced(user_id: int, message: str, session_id: str):
    """
    進化型チャット（終了判定込み）
    """
    
    # 1. メッセージ処理
    manager = UserProfileManager(user_id)
    manager.save_chat_message(session_id, 'user', message)
    manager.extract_and_save_insights(message)
    manager.update_conversation_embedding(session_id)
    
    # 2. 会話コンテキスト取得
    context = get_conversation_context(user_id, session_id)
    
    # 3. 終了判定 🎯
    controller = ConversationEndController()
    decision = controller.should_end_conversation(context)
    
    if decision['should_end']:
        # 会話終了 → 最終推薦
        
        # 最終マッチング実行
        matcher = AdvancedMatcher(user_id)
        final_recommendations = matcher.get_final_recommendations()
        
        # ボットメッセージ
        bot_message = f"""
{decision['message']}

{generate_summary(context['user_profile'])}

厳選した{len(final_recommendations)}件の求人をご紹介します。
"""
        
        manager.save_chat_message(session_id, 'bot', bot_message)
        
        return {
            'conversation_ended': True,
            'message': bot_message,
            'recommendations': final_recommendations,
            'reason': decision['reason']
        }
    
    else:
        # 会話続行 → 次の質問
        
        # 現在の候補を取得
        matcher = AdvancedMatcher(user_id)
        current_candidates = matcher.get_current_candidates()
        
        # 次の質問を生成
        generator = EvolvingQuestionGenerator(user_id)
        next_question = generator.generate_next_question(current_candidates)
        
        # ボットメッセージ
        bot_message = f"""
{len(current_candidates)}件の候補があります。

{next_question['question_text']}
"""
        
        manager.save_chat_message(session_id, 'bot', bot_message)
        
        return {
            'conversation_ended': False,
            'message': bot_message,
            'candidate_count': len(current_candidates),
            'profile_completeness': context['profile_completeness']
        }


def get_conversation_context(user_id, session_id):
    """
    会話コンテキストを取得
    """
    
    # 会話履歴
    conversation_history = get_chat_history(user_id, session_id)
    
    # ユーザープロファイル
    user_profile = get_comprehensive_profile(user_id)
    
    # スコア履歴
    score_history = get_score_history(session_id)
    
    # 現在の候補
    current_candidates = get_current_candidates(user_id)
    
    return {
        'conversation_turns': len(conversation_history) // 2,  # ユーザー発言数
        'profile_completeness': calculate_profile_completeness(user_profile),
        'score_convergence': calculate_score_convergence(score_history),
        'recommendation_confidence': calculate_recommendation_confidence(current_candidates),
        'user_satisfaction': estimate_user_satisfaction(
            [msg for msg in conversation_history if msg['sender'] == 'user']
        ),
        'user_profile': user_profile,
        'score_history': score_history
    }


def generate_summary(user_profile):
    """
    ユーザーの希望をまとめて表示
    """
    
    summary_parts = []
    
    if user_profile.get('career_goal'):
        summary_parts.append(f"目標: {user_profile['career_goal']}")
    
    priorities = []
    if user_profile.get('work_life_balance_priority', 0) >= 4:
        priorities.append('ワークライフバランス')
    if user_profile.get('career_growth_priority', 0) >= 4:
        priorities.append('キャリア成長')
    
    if priorities:
        summary_parts.append(f"重視: {', '.join(priorities)}")
    
    if user_profile.get('learning_interests'):
        summary_parts.append(
            f"学習: {', '.join(user_profile['learning_interests'][:3])}"
        )
    
    return """
整理すると:
""" + '\n'.join(f"✅ {part}" for part in summary_parts)
```

---

# 5. まとめ

## ✅ 進化型システムの終了条件

### 単純な「件数」ではなく、以下を総合判断:

1. **最低ターン数**: 5回以上
2. **情報充足度**: 70%以上
3. **スコア収束度**: 上位候補が安定
4. **推薦信頼度**: 0.8以上
5. **ユーザー満足度**: 早期終了希望の検出

### 終了パターン

- **理想的終了**: すべての条件クリア（6-7回）
- **十分な情報**: 主要条件クリア（5-6回）
- **スコア収束**: これ以上質問しても変わらない（7-8回）
- **早期終了**: ユーザーの要望（3-4回）
- **最大ターン**: 安全装置（10回）

---

## 🔄 既存システムとの違い

```
既存システム:
IF 候補件数 <= 3:
    終了

進化型システム:
IF (ターン数 >= 5 AND 充足度 >= 70 AND 信頼度 >= 0.8)
OR (スコア収束 AND 充足度 >= 60)
OR (ユーザー早期終了希望)
OR (ターン数 >= 10):
    終了
```

---

**進化型は「賢い終了判定」で最適なタイミングを見極めます！** 🎯
