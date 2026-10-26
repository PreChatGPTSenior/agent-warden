package lab.stoneshelter.mappers.dtos;

/** Demonstrates the DTO mapper declaration shape. */
public class StoneEntityToStoneResponseMapper extends AbstractDtoMapper {
  /** Returns a scalar example result; runtime mapping is outside this fixture. */
  public long toDto(long id) {
    return id;
  }
}
