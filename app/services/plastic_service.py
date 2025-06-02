from sqlmodel import Session, select
from models import PlasticBag
from typing import Tuple
from sqlalchemy import cast, Integer
MAX_BAGS_PER_LAYER = 5
MAX_LAYERS_PER_PAIR = 20

def get_current_pallet_layer(session: Session) -> Tuple[str, int]:
    pallets = session.exec(
        select(PlasticBag.pallet).distinct().order_by(PlasticBag.id)).all()
    last_main_pallet = None
    # lay danh sach pallet
    for pallet in reversed(pallets):
        if pallet.endswith(".1"):
            last_main_pallet = pallet
            break
    # neu da co pallet
    if last_main_pallet:
        code = int(last_main_pallet.split(".")[0])
        pallet1 = f"{code}.1"
        bags = session.exec(select(PlasticBag).where(PlasticBag.pallet == pallet1)).all()
        total_bags = len(bags)
        # pallet day doi sang pallet moi
        if total_bags >= MAX_BAGS_PER_LAYER * MAX_LAYERS_PER_PAIR:
            new_code = code + 1
            return f"{new_code}.1", 1
        # neu chua day xu ly layer hien tai
        layers = [b.layer for b in bags]
        max_layer = max(layers)
        bags_in_layer = len([b for b in bags if b.layer == max_layer])
        if bags_in_layer >= MAX_BAGS_PER_LAYER:
            return pallet1, max_layer + 1
        else:
            return pallet1, max_layer
    else:
        # turong hop chua co pallet
        return "1.1", 1


def add_new_lot(code:str,lot:str,session:Session):
    pallet,layer=get_current_pallet_layer(session)
    bag=PlasticBag(
        code=code,
        lot=lot,
        pallet=pallet,
        layer=layer
    )
    session.add(bag)
    session.commit()
    return f"add code {code} lot {lot} in pallet {pallet} layer {layer}"

def get_current_location(code:str,lot:str,session:Session) -> str:
    bag=session.exec(select(PlasticBag).where(PlasticBag.code == code).where(PlasticBag.lot == lot).order_by(PlasticBag.id.desc())).first()
    if not bag:
        raise ValueError(f"No bag found with code {code} and lot {lot}")
    return bag.code, bag.lot,bag.pallet, bag.layer

def prepare_retrieval(code:str,lot:str,target_layer:int,session:Session):
    current_bag=session.exec(select(PlasticBag).where(PlasticBag.code == code).where(PlasticBag.lot == lot)).first()
    if not current_bag:
        return f"cannot found"
    base=current_bag.pallet.split('.')[0]
    is_main=current_bag.pallet.endswith(".1")
    source_pallet=f"{base}.1" if is_main else f"{base}.2"
    dest_pallet=f"{base}.2" if is_main else f"{base}.1"
    store_pallet=f"{base}.store"
    all_bags = session.exec(
    select(PlasticBag).where(
        PlasticBag.pallet == source_pallet
    )
).all()
    print(f'all bag{all_bags}')
    bags_to_move = [b for b in all_bags if b.layer > target_layer]
    bags_to_move.sort(key=lambda b: b.id, reverse=False)
    print(bags_to_move)
    remainder=len(bags_to_move)%MAX_BAGS_PER_LAYER
    
    if remainder:
        partial=bags_to_move[-remainder:]
        for bag in partial:
            bag.pallet=store_pallet
        bags_to_move=bags_to_move[:-remainder]

    existing_layers = [x for x in session.exec(select(PlasticBag.layer).where(PlasticBag.pallet == dest_pallet)).all()]
    max_existing= max(existing_layers) if existing_layers else 0
    new_layer=max_existing + 1

    for i in range(0,len(bags_to_move),MAX_BAGS_PER_LAYER):
        group=bags_to_move[::-1][i:i+MAX_BAGS_PER_LAYER]
        for bag in group:
            bag.pallet=dest_pallet
            bag.layer=new_layer
        new_layer += 1
    session.commit()
    return (
        f"Prepared to retrieve layer {target_layer} from pallet {source_pallet}."
        f"Moved {len(bags_to_move)} bags to pallet {dest_pallet}."
        + (f"Moved {remainder} bags to {store_pallet}." if remainder else "")
    )

