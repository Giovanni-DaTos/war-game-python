import pygame
import sys
import random
import math

# --- INIZIALIZZAZIONE ---
pygame.init()
WIDTH, HEIGHT = 800, 600
WORLD_WIDTH, WORLD_HEIGHT = 2400, 1800 
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cyber Survivor: Tactical Strike 2.0")
clock = pygame.time.Clock()
fullscreen = False

# --- VARIABILI GLOBALI ---
shake_intensity = 0
cam_x, cam_y = 0, 0 
target_cam_x, target_cam_y = 0, 0 

# --- CARICAMENTO ASSET ---
def load_img(name, size=None):
    try:
        img = pygame.image.load(name).convert_alpha()
        for x in range(img.get_width()):
            for y in range(img.get_height()):
                rgba = img.get_at((x, y))
                if rgba[0] > 210 and rgba[1] > 210 and rgba[2] > 210:
                    img.set_at((x, y), (0, 0, 0, 0))
        if size: img = pygame.transform.scale(img, size)
        return img
    except:
        surf = pygame.Surface(size if size else (50, 50)); surf.fill((255, 0, 255))
        return surf

img_player = load_img("personaggio.png", (55, 65))
img_nemico = load_img("nemico.png", (50, 50))
img_elite = load_img("nemico_elite.jpg", (65, 65))
img_boss = load_img("boss.png", (140, 140))
img_sfondo = load_img("sfondo_alto.png", (800, 600))
img_benda = load_img("benda.jpg", (35, 35))
img_shotgun = load_img("fucile_a_pompa.png", (50, 30))
img_mg = load_img("mitragliatrice.png", (50, 30))

img_flip_x = pygame.transform.flip(img_sfondo, True, False)
img_flip_y = pygame.transform.flip(img_sfondo, False, True)
img_flip_both = pygame.transform.flip(img_sfondo, True, True)

stars = [[random.randint(0, WIDTH), random.randint(0, HEIGHT), random.random() * 3] for _ in range(80)]

# --- CLASSI ---
class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.color = color
        self.vx, self.vy = random.uniform(-4, 4), random.uniform(-4, 4)
        self.lifetime = 30
    def update(self):
        self.x += self.vx; self.y += self.vy; self.lifetime -= 1
    def draw(self, surf):
        if self.lifetime > 0:
            pygame.draw.circle(surf, self.color, (int(self.x - cam_x), int(self.y - cam_y)), 3)

class Bullet:
    def __init__(self, x, y, target_x, target_y, owner="player", damage=1, speed=10, is_special=False):
        self.x, self.y = x, y
        angle = math.atan2(target_y - (y - cam_y), target_x - (x - cam_x))
        self.dx, self.dy = math.cos(angle) * speed, math.sin(angle) * speed
        self.owner, self.damage = owner, damage
        self.is_special = is_special
        self.rect = pygame.Rect(x, y, 8, 8)
    def update(self):
        self.x += self.dx; self.y += self.dy
        self.rect.topleft = (self.x, self.y)

class Enemy:
    def __init__(self, is_elite=False, is_boss=False):
        self.is_boss, self.is_elite = is_boss, is_elite
        size = (140, 140) if is_boss else ((65, 65) if is_elite else (50, 50))
        self.x = random.randint(0, WORLD_WIDTH)
        self.y = random.randint(0, WORLD_HEIGHT)
        self.rect = pygame.Rect(self.x, self.y, size[0], size[1])
        if is_boss: self.hp, self.max_hp, self.fire_rate, self.bullet_dmg, self.speed = 2000, 2000, 800, 20, 1.3
        elif is_elite: self.hp, self.fire_rate, self.bullet_dmg, self.speed = 20, 1500, 10, 2.4
        else: self.hp, self.fire_rate, self.bullet_dmg, self.speed = 8, 2500, 5, 2.1
        self.last_shot = pygame.time.get_ticks()

    def update(self, p_x, p_y):
        dx, dy = p_x - self.x, p_y - self.y
        dist = math.hypot(dx, dy)
        if dist > 5:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed
        self.rect.topleft = (self.x, self.y)

class Item:
    def __init__(self, type, x, y):
        self.type = type
        self.x, self.y = x, y
        self.rect = pygame.Rect(x, y, 35, 35)
        self.img = img_shotgun if type == "SHOTGUN" else (img_mg if type == "MG" else img_benda)
        self.glow_timer = random.uniform(0, 100)

WEAPONS = {
    "BASE": {"dmg": 2, "ammo": 25, "kb": 5, "speed": 12, "rate": 200},
    "SHOTGUN": {"dmg": 6, "ammo": 6, "kb": 60, "speed": 14, "rate": 650},
    "MG": {"dmg": 1.2, "ammo": 120, "kb": 15, "speed": 18, "rate": 85},
    "EMILY": {"dmg": 9999, "ammo": 999, "kb": 300, "speed": 25, "rate": 50} 
}

def reset_game():
    global player_x, player_y, player_hp, ammo, round_count, killed_count, score, current_weapon
    global bullets, enemies, items, particles, game_state, boss_active, enemy_queue
    global last_spawn_time, player_inv_timer, last_player_shot, input_buffer, dash_timer
    player_x, player_y = WORLD_WIDTH // 2, WORLD_HEIGHT // 2
    player_hp, ammo, round_count, killed_count, score = 100, 25, 1, 0, 0
    current_weapon = "BASE"
    bullets, enemies, items, particles, enemy_queue = [], [], [], [], []
    game_state, boss_active = "MENU", False
    last_spawn_time, player_inv_timer, last_player_shot = 0, 0, 0
    dash_timer, input_buffer = 0, ""
    spawn_round_logic()

def spawn_round_logic():
    global enemy_queue, items
    enemy_queue = []
    if round_count < 15:
        n_normals = 5 + round_count
        n_elites = min(round_count, 10) if round_count >= 5 else 0
        for _ in range(n_normals): enemy_queue.append(False)
        for _ in range(n_elites): enemy_queue.append(True)
        random.shuffle(enemy_queue)
    items.append(Item(random.choice(["SHOTGUN", "MG", "BENDA"]), random.randint(200, WORLD_WIDTH-200), random.randint(200, WORLD_HEIGHT-200)))

def draw_minimap():
    mm_w, mm_h = 160, 120
    mm_x, mm_y = WIDTH - mm_w - 20, 20
    mm_surf = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
    mm_surf.fill((0, 0, 0, 180))
    pygame.draw.rect(mm_surf, (0, 255, 255), (0, 0, mm_w, mm_h), 1)
    scale_x, scale_y = mm_w / WORLD_WIDTH, mm_h / WORLD_HEIGHT
    
    # Player
    pygame.draw.circle(mm_surf, (0, 255, 255), (int(player_x * scale_x), int(player_y * scale_y)), 3)
    
    # Nemici
    for e in enemies:
        color = (255, 0, 0) if not e.is_boss else (255, 255, 0)
        pygame.draw.circle(mm_surf, color, (int(e.x * scale_x), int(e.y * scale_y)), 2)
    
    # --- DROP SULLA MINIMAPPA ---
    for it in items:
        # Verde per cure, Viola per armi
        it_color = (0, 255, 100) if it.type == "BENDA" else (200, 0, 255)
        pygame.draw.rect(mm_surf, it_color, (int(it.x * scale_x), int(it.y * scale_y), 3, 3))
        
    screen.blit(mm_surf, (mm_x, mm_y))

def draw_end_screen(status):
    screen.fill((10, 10, 20))
    color = (255, 50, 50) if status == "LOSE" else (50, 255, 100)
    font_main = pygame.font.SysFont("Impact", 70)
    msg = "MISSIONE FALLITA" if status == "LOSE" else "MISSIONE COMPIUTA"
    surf = font_main.render(msg, True, color)
    screen.blit(surf, (WIDTH//2 - surf.get_width()//2, HEIGHT//2 - 50))
    font_sub = pygame.font.SysFont("Arial", 30, True)
    screen.blit(font_sub.render(f"Punteggio: {score} | Premi R per ricominciare", True, (255,255,255)), (WIDTH//2 - 200, HEIGHT//2 + 50))

reset_game()

# --- LOOP PRINCIPALE ---
while True:
    now = pygame.time.get_ticks()
    
    if game_state == "PLAYING":
        target_cam_x = player_x - WIDTH // 2
        target_cam_y = player_y - HEIGHT // 2
        target_cam_x = max(0, min(target_cam_x, WORLD_WIDTH - WIDTH))
        target_cam_y = max(0, min(target_cam_y, WORLD_HEIGHT - HEIGHT))
        cam_x += (target_cam_x - cam_x) * 0.1
        cam_y += (target_cam_y - cam_y) * 0.1

    off_x = random.randint(-shake_intensity, shake_intensity) if shake_intensity > 0 else 0
    off_y = random.randint(-shake_intensity, shake_intensity) if shake_intensity > 0 else 0
    if shake_intensity > 0: shake_intensity -= 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit()
        if event.type == pygame.KEYDOWN:
            char = event.unicode.upper()
            if char.isalpha():
                input_buffer = (input_buffer + char)[-5:]
                if "EMILY" in input_buffer:
                    current_weapon = "EMILY"; ammo = 999
            if event.key == pygame.K_f:
                fullscreen = not fullscreen
                screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN) if fullscreen else pygame.display.set_mode((WIDTH, HEIGHT))
            if event.key == pygame.K_SPACE and dash_timer <= 0: dash_timer = 35
            if event.key == pygame.K_r:
                if game_state in ["GAME_OVER", "VICTORY"]: reset_game()
                elif current_weapon == "BASE": ammo = 25
            if event.key == pygame.K_ESCAPE: game_state = "PLAYING" if game_state == "MENU" else "MENU"

    if game_state == "PLAYING":
        speed = 14 if dash_timer > 25 else 4.8
        if dash_timer > 0: dash_timer -= 1
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a] and player_x > 0: player_x -= speed
        if keys[pygame.K_d] and player_x < WORLD_WIDTH - 50: player_x += speed
        if keys[pygame.K_w] and player_y > 0: player_y -= speed
        if keys[pygame.K_s] and player_y < WORLD_HEIGHT - 60: player_y += speed

        # --- RENDERING MAPPA ---
        tile_w, tile_h = img_sfondo.get_width(), img_sfondo.get_height()
        for x in range(0, WORLD_WIDTH, tile_w):
            for y in range(0, WORLD_HEIGHT, tile_h):
                if x - cam_x < WIDTH and x - cam_x + tile_w > 0:
                    if y - cam_y < HEIGHT and y - cam_y + tile_h > 0:
                        ix, iy = x // tile_w, y // tile_h
                        if ix % 2 == 0:
                            img = img_sfondo if iy % 2 == 0 else img_flip_y
                        else:
                            img = img_flip_x if iy % 2 == 0 else img_flip_both
                        screen.blit(img, (x - cam_x + off_x, y - cam_y + off_y))

        # Sparo
        if pygame.mouse.get_pressed()[0] and (ammo > 0 or current_weapon == "EMILY"):
            w = WEAPONS[current_weapon]
            if now - last_player_shot > w["rate"]:
                if current_weapon != "EMILY": ammo -= 1
                mx, my = pygame.mouse.get_pos()
                bullets.append(Bullet(player_x+25, player_y+30, mx, my, "player", w["dmg"], w["speed"], current_weapon=="EMILY"))
                last_player_shot = now
                if current_weapon == "EMILY": shake_intensity = 6
                if ammo <= 0 and current_weapon not in ["BASE", "EMILY"]: current_weapon, ammo = "BASE", 25

        # Gestione Nemici
        if enemy_queue and now - last_spawn_time > 800:
            enemies.append(Enemy(is_elite=enemy_queue.pop())); last_spawn_time = now
        if round_count == 15 and not enemies and not enemy_queue and not boss_active:
            enemies.append(Enemy(is_boss=True)); boss_active = True

        for b in bullets[:]:
            b.update()
            if b.owner == "player":
                for e in enemies[:]:
                    if b.rect.colliderect(e.rect):
                        e.hp -= b.damage
                        if e.hp <= 0:
                            for _ in range(10): particles.append(Particle(e.x, e.y, (200, 0, 0)))
                            score += 1000 if e.is_boss else 50
                            if e.is_boss: game_state = "VICTORY"
                            enemies.remove(e)
                        if b in bullets: bullets.remove(b)
                        break
            elif b.rect.colliderect(pygame.Rect(player_x, player_y, 45, 55)) and dash_timer < 25:
                player_hp -= b.damage; bullets.remove(b); shake_intensity = 10
            
            if 0 <= b.x <= WORLD_WIDTH and 0 <= b.y <= WORLD_HEIGHT:
                color = (255, 0, 255) if b.is_special else (255, 255, 0)
                if b.owner == "enemy": color = (255, 50, 50)
                if b in bullets:
                    pygame.draw.circle(screen, color, (int(b.x - cam_x + off_x), int(b.y - cam_y + off_y)), 5)
            elif b in bullets: bullets.remove(b)

        for e in enemies:
            e.update(player_x, player_y)
            if now - e.last_shot > e.fire_rate:
                bullets.append(Bullet(e.x+25, e.y+25, player_x+25, player_y+25, "enemy", e.bullet_dmg, 6))
                e.last_shot = now
            img = img_boss if e.is_boss else (img_elite if e.is_elite else img_nemico)
            screen.blit(img, (e.x - cam_x + off_x, e.y - cam_y + off_y))
            if e.is_boss:
                pygame.draw.rect(screen, (255,0,0), (WIDTH//2-150, 20, 300*(e.hp/e.max_hp), 15))

        # --- LOGICA DROP SBRILLUCCICANTI ---
        for it in items[:]:
            it.glow_timer += 0.1
            pulse = math.sin(it.glow_timer) * 8 # Effetto pulsazione
            
            if pygame.Rect(player_x, player_y, 45, 55).colliderect(it.rect):
                if it.type == "BENDA": player_hp = min(100, player_hp + 30)
                else: current_weapon, ammo = it.type, WEAPONS[it.type]["ammo"]
                items.remove(it)
            else:
                # Disegna lo sbrilluccichio (alone colorato sotto l'oggetto)
                glow_color = (0, 255, 150) if it.type == "BENDA" else (200, 50, 255)
                glow_size = 20 + pulse
                glow_surf = pygame.Surface((glow_size*2, glow_size*2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*glow_color, 100), (int(glow_size), int(glow_size)), int(glow_size))
                screen.blit(glow_surf, (it.x - cam_x - glow_size + 17, it.y - cam_y - glow_size + 17), special_flags=pygame.BLEND_ADD)
                
                # Disegna l'immagine dell'oggetto leggermente oscillante
                screen.blit(it.img, (it.x - cam_x, it.y - cam_y + (pulse/2)))

        for p in particles[:]:
            p.update(); p.draw(screen)
            if p.lifetime <= 0: particles.remove(p)

        if player_inv_timer > 0: player_inv_timer -= 1
        if player_inv_timer % 4 == 0:
            screen.blit(img_player, (player_x - cam_x + off_x, player_y - cam_y + off_y))

        draw_minimap()
        f_ui = pygame.font.SysFont("Impact", 22)
        screen.blit(f_ui.render(f"HP: {player_hp} | AMMO: {ammo if current_weapon!='EMILY' else 'INF'} | ROUND: {round_count}", True, (255,255,255)), (20, HEIGHT-40))

        if not enemies and not enemy_queue and round_count < 15:
            round_count += 1; spawn_round_logic()
        if player_hp <= 0: game_state = "GAME_OVER"

    elif game_state == "MENU":
        screen.fill((0,0,0))
        for s in stars:
            s[1] = (s[1] + s[2]) % HEIGHT
            pygame.draw.circle(screen, (255,255,255), (int(s[0]), int(s[1])), 1)
        
        f_m = pygame.font.SysFont("Impact", 65)
        title_surf = f_m.render("CYBER SURVIVOR 2.0", True, (0, 255, 0))
        screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 100))
        
        f_s = pygame.font.SysFont("Arial", 22, True)
        comandi = [
            "WASD: Movimento Personaggio",
            "MOUSE: Mira e Fuoco",
            "SPAZIO: Dash (Scatto Rapido)",
            "R: Ricarica / Ricomincia",
            "F: Schermo Intero",
            "",
            "PREMI 'ESC' PER INIZIARE"
        ]
        
        for i, riga in enumerate(comandi):
            colore = (0, 255, 255) if "ESC" in riga else (200, 200, 200)
            txt_surf = f_s.render(riga, True, colore)
            screen.blit(txt_surf, (WIDTH // 2 - txt_surf.get_width() // 2, 240 + i * 35))

    elif game_state == "GAME_OVER": draw_end_screen("LOSE")
    elif game_state == "VICTORY": draw_end_screen("WIN")

    pygame.display.flip()
    clock.tick(60)