let currentBoardSize = 9;
if (typeof API_BASE === 'undefined') {
    var API_BASE = window.location.origin.includes('5500')
        ? window.location.origin.replace(':5500', ':5000')
        : (window.location.protocol === 'file:' ? 'http://127.0.0.1:5000' : window.location.origin);
}

const pieceMap = {
    1: { char: '🪨', class: 'piece-red' },
    2: { char: '📄', class: 'piece-red' },
    3: { char: '✂️', class: 'piece-red' },
    4: { char: '🪨', class: 'piece-blue' },
    5: { char: '📄', class: 'piece-blue' },
    6: { char: '✂️', class: 'piece-blue' }
};

let currentBoard = [];

function initializeBoard(boardSize = 9) {
    currentBoardSize = boardSize;
    const boardDiv = document.getElementById('board');
    if (!boardDiv) return;
    
    boardDiv.innerHTML = '';
    boardDiv.style.gridTemplateColumns = `repeat(${boardSize}, 45px)`;
    boardDiv.style.gridTemplateRows = `repeat(${boardSize}, 45px)`;

    currentBoard = [];
    for (let r = 0; r < boardSize; r++) {
        let row = [];
        for (let c = 0; c < boardSize; c++) {
            const cell = document.createElement('div');
            cell.className = 'cell';
            cell.id = `cell-${r}-${c}`;
            
            if (r === 0 && c === 0) cell.classList.add('red-dest');
            if (r === boardSize - 1 && c === boardSize - 1) cell.classList.add('blue-dest');
            
            boardDiv.appendChild(cell);
            row.push(0);
        }
        currentBoard.push(row);
    }
}

function renderBoard(boardState) {
    const boardSize = boardState.length;
    
    if (boardSize !== currentBoardSize) {
        initializeBoard(boardSize);
    }

    for (let r = 0; r < boardSize; r++) {
        for (let c = 0; c < boardSize; c++) {
            const val = boardState[r][c];
            const cell = document.getElementById(`cell-${r}-${c}`);
            if (!cell) continue;

            if (val === -1) {
                cell.className = 'cell obstacle';
                cell.innerHTML = '🧱';
            } else if (val === 0) {
                cell.innerHTML = '';
                cell.className = 'cell';
                if (r === 0 && c === 0) cell.classList.add('red-dest');
                if (r === boardSize - 1 && c === boardSize - 1) cell.classList.add('blue-dest');
            } else if (pieceMap[val]) {
                cell.className = 'cell';
                if (r === 0 && c === 0) cell.classList.add('red-dest');
                if (r === boardSize - 1 && c === boardSize - 1) cell.classList.add('blue-dest');
                cell.innerHTML = `<span class="${pieceMap[val].class}">${pieceMap[val].char}</span>`;
            }
            currentBoard[r][c] = val;
        }
    }
}

function renderMove(move) {
    const r1 = move.from[0], c1 = move.from[1];
    const r2 = move.to[0], c2 = move.to[1];
    
    const movingPiece = currentBoard[r1][c1];
    currentBoard[r1][c1] = 0;
    currentBoard[r2][c2] = movingPiece;
    
    renderBoard(currentBoard);
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function playReplay(matchData) {
    document.getElementById('team-names').innerText = `${matchData.red_team || 'RED'} vs ${matchData.blue_team || 'BLUE'}`;
    document.getElementById('match-status').innerText = 'Playing... (3s delay per move)';
    
    renderBoard(matchData.initial_board);
    
    for (const move of matchData.moves) {
        await sleep(3000);
        renderMove(move);
    }
    
    document.getElementById('match-status').innerText = `Finished! Result: ${matchData.result ? matchData.result.winner : 'Completed'}`;
}

initializeBoard();