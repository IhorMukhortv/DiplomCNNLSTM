import os
import graphviz

def generate_cnn_lstm_diagram():
    dot = graphviz.Digraph(comment='CNN-LSTM Data Flow', format='png')
    dot.attr(rankdir='TD', size='8,10')
    dot.attr('node', shape='box', style='rounded,filled', fillcolor='lightblue', fontname='Arial')

    dot.node('Input', 'Вхідні дані:\nМетеопараметри (GHI, DNI, DHI, T, RH, Хмарність)\n+\nФактична потужність (t-24..t-1)', fillcolor='lightyellow')
    dot.node('Norm', 'Мін-макс нормалізація\n(Scaling 0..1)')
    dot.node('CNN', 'Згортковий шар (Conv1D)\nВиділення локальних\nпогодно-просторових ознак', fillcolor='lightgreen')
    dot.node('Pool', 'Шар субдискретизації\n(MaxPooling1D)\nЗменшення розмірності')
    dot.node('LSTM', 'Рекурентний шар (LSTM)\nАналіз часових залежностей\nта добових трендів', fillcolor='lightpink')
    dot.node('Dropout', 'Шар регуляризації\n(Dropout 0.2)')
    dot.node('Dense', 'Повнозв\'язний шар\n(Dense 32, ReLU)')
    dot.node('Output', 'Вихідний шар (Dense 1)\nПрогноз потужності (t)', fillcolor='lightcoral')
    dot.node('Denorm', 'Обернена нормалізація\n(Inverse Scaling)\nкВт', fillcolor='lightyellow')

    dot.edge('Input', 'Norm')
    dot.edge('Norm', 'CNN')
    dot.edge('CNN', 'Pool')
    dot.edge('Pool', 'LSTM')
    dot.edge('LSTM', 'Dropout')
    dot.edge('Dropout', 'Dense')
    dot.edge('Dense', 'Output')
    dot.edge('Output', 'Denorm')

    out_path = os.path.join('docs', 'images', 'cnn_lstm_data_flow')
    dot.render(out_path, cleanup=True)
    print(f"Generated {out_path}.png")


def generate_architecture_diagram():
    dot = graphviz.Digraph(comment='System Architecture', format='png')
    dot.attr(rankdir='TB', size='10,12', splines='ortho')
    dot.attr('node', shape='box', style='rounded,filled', fillcolor='#e6f2ff', fontname='Arial', margin='0.2')

    dot.node('Client', 'Клієнт / Споживач', fillcolor='#ffebcc')
    dot.node('Uvicorn', 'ASGI Uvicorn\n(Асинхронний сервер)', fillcolor='#d9f2d9')
    dot.node('Router', 'FastAPI App\n(API Endpoints Router)')
    dot.node('Session', 'SQLAlchemy Session\n(Async)')
    dot.node('Scaler', 'MinMax Scaler\n(Data Prep)')
    dot.node('Model', 'CNN-LSTM Model\n(TensorFlow/Keras)', fillcolor='#ffe6e6')
    dot.node('DB', 'TimescaleDB (PostgreSQL)\nБаза даних часових рядів', fillcolor='#e6e6ff', shape='cylinder')

    dot.edge('Client', 'Uvicorn', dir='forward')
    dot.edge('Uvicorn', 'Client', dir='forward')

    dot.edge('Uvicorn', 'Router', dir='both')
    dot.edge('Router', 'Session', dir='both')
    dot.edge('Router', 'Scaler', dir='both')
    dot.edge('Scaler', 'Model', dir='forward')
    dot.edge('Model', 'Router', dir='forward')

    dot.edge('Session', 'DB', label=' Async Query / Records', dir='both')

    out_path = os.path.join('docs', 'images', 'architecture_flow')
    dot.render(out_path, cleanup=True)
    print(f"Generated {out_path}.png")

def generate_online_learning_diagram():
    dot = graphviz.Digraph(comment='Online Learning Flow', format='png')
    dot.attr(rankdir='TB', size='8,10')
    dot.attr('node', shape='box', style='rounded,filled', fillcolor='#f9f9f9', fontname='Arial')

    dot.node('DB', 'База даних (TimescaleDB)', shape='cylinder', fillcolor='#e6e6ff')
    dot.node('Load', 'Завантаження та перевірка даних\n(N >= 25)')
    dot.node('Scale', 'Масштабування через\nglobal_scaler')
    dot.node('Windows', 'Формування вікон зсуву\n(lookback=24, horizon=1) ──> X, y')
    dot.node('Clone', 'Клонування базової моделі\n(fresh copy)')
    dot.node('Compile', 'Компіляція клону\n(lr = 0.0001)')
    dot.node('MSE1', 'Розрахунок MSE_before')
    dot.node('Train', 'Донавчання клону в окремому потоці\n(asyncio.to_thread)', fillcolor='#ffcccc')
    dot.node('MSE2', 'Розрахунок MSE_after')
    dot.node('Save', 'Збереження у відповідний іменований слот\nреєстру (year / month)', fillcolor='#ccffcc')

    dot.edge('DB', 'Load', dir='forward')
    dot.edge('Load', 'Scale')
    dot.edge('Scale', 'Windows')
    dot.edge('Windows', 'Clone')
    dot.edge('Clone', 'Compile')
    dot.edge('Compile', 'MSE1')
    dot.edge('MSE1', 'Train')
    dot.edge('Train', 'MSE2')
    dot.edge('MSE2', 'Save')

    out_path = os.path.join('docs', 'images', 'online_learning_flow')
    dot.render(out_path, cleanup=True)
    print(f"Generated {out_path}.png")

if __name__ == '__main__':
    generate_cnn_lstm_diagram()
    generate_architecture_diagram()
    generate_online_learning_diagram()
