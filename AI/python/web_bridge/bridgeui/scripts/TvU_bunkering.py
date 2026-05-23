"""벙커링: 앞마당/입구 벙커+SCV 초반 올인
TvZ_2rax(바이오닉+SCV 러쉬) 오프닝을 활용.
수동 모드로 전환 후 입구 막기를 실행.
"""


def run(ctx):
    ctx.set_opening("TvZ_2rax")
    ctx.log("벙커링: 2 Rax 오프닝으로 시작")

    ctx.log("벙커링: 수동 모드 전환 후 입구 차단")
    ctx.control("block_entrance")
