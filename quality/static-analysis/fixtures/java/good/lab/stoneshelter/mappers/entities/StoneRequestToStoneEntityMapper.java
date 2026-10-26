package lab.stoneshelter.mappers.entities;

/** Demonstrates the mapper declaration shape. */
public class StoneRequestToStoneEntityMapper extends AbstractEntityMapper {
  /** Returns the entity, preserving entity-first update order. */
  public StoneEntity toEntity(StoneEntity stoneEntity, StoneRequest stoneRequest) {
    return stoneEntity;
  }
}
