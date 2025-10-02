"""Main entry point for the Fantasy Football Valuation Engine."""

import click
import logging
from pathlib import Path

from valuation_engine import ProjectionEngine, ScoringSystem
from valuation_engine.utils.logging_config import setup_logging


@click.group()
@click.option('--log-level', default='INFO', 
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Set logging level')
@click.option('--log-file', type=click.Path(), help='Log file path')
def cli(log_level, log_file):
    """Fantasy Football Valuation Engine CLI."""
    setup_logging(level=log_level, log_file=log_file)


@cli.command()
@click.option('--scoring', '-s', default='ppr',
              type=click.Choice(['standard', 'ppr', 'half_ppr']),
              help='Fantasy scoring system')
@click.option('--week', '-w', type=int, required=True,
              help='Target week number')
@click.option('--season', '-y', type=int,
              help='Target season (defaults to current)')
@click.option('--positions', '-p', multiple=True,
              type=click.Choice(['QB', 'RB', 'WR', 'TE']),
              help='Positions to include (default: all)')
@click.option('--output', '-o', type=click.Path(),
              help='Output file path (CSV format)')
def weekly(scoring, week, season, positions, output):
    """Generate weekly fantasy point projections."""
    click.echo(f"Generating weekly projections for week {week}...")
    
    # Initialize engine
    engine = ProjectionEngine(scoring_system=scoring)
    
    # Generate projections
    projections = engine.get_weekly_projections(
        week=week,
        season=season,
        positions=list(positions) if positions else None
    )
    
    if projections.empty:
        click.echo("No projections generated.", err=True)
        return
    
    # Display results
    click.echo(f"\nTop 20 Weekly Projections (Week {week}):")
    click.echo("=" * 60)
    
    display_cols = ['player_name', 'position', 'team', 'projected_points', 
                   'confidence_lower', 'confidence_upper']
    top_20 = projections.head(20)[display_cols]
    
    for _, row in top_20.iterrows():
        click.echo(f"{row['player_name']:20} {row['position']:3} {row['team']:4} "
                  f"{row['projected_points']:6.1f} pts "
                  f"({row['confidence_lower']:4.1f}-{row['confidence_upper']:4.1f})")
    
    # Save to file if requested
    if output:
        projections.to_csv(output, index=False)
        click.echo(f"\nProjections saved to {output}")
    
    click.echo(f"\nGenerated {len(projections)} total projections.")


@cli.command()
@click.option('--scoring', '-s', default='ppr',
              type=click.Choice(['standard', 'ppr', 'half_ppr']),
              help='Fantasy scoring system')
@click.option('--season', '-y', type=int,
              help='Target season (defaults to current)')
@click.option('--positions', '-p', multiple=True,
              type=click.Choice(['QB', 'RB', 'WR', 'TE']),
              help='Positions to include (default: all)')
@click.option('--output', '-o', type=click.Path(),
              help='Output file path (CSV format)')
def seasonal(scoring, season, positions, output):
    """Generate seasonal fantasy point projections."""
    click.echo(f"Generating seasonal projections for {season or 'current season'}...")
    
    # Initialize engine
    engine = ProjectionEngine(scoring_system=scoring)
    
    # Generate projections
    projections = engine.get_seasonal_projections(
        season=season,
        positions=list(positions) if positions else None
    )
    
    if projections.empty:
        click.echo("No projections generated.", err=True)
        return
    
    # Display results
    click.echo(f"\nTop 20 Seasonal Projections:")
    click.echo("=" * 70)
    
    display_cols = ['player_name', 'position', 'team', 'projected_points', 
                   'confidence_lower', 'confidence_upper', 'expected_games']
    top_20 = projections.head(20)[display_cols]
    
    for _, row in top_20.iterrows():
        click.echo(f"{row['player_name']:20} {row['position']:3} {row['team']:4} "
                  f"{row['projected_points']:6.1f} pts "
                  f"({row['confidence_lower']:5.1f}-{row['confidence_upper']:5.1f}) "
                  f"[{row['expected_games']:4.1f} games]")
    
    # Save to file if requested
    if output:
        projections.to_csv(output, index=False)
        click.echo(f"\nProjections saved to {output}")
    
    click.echo(f"\nGenerated {len(projections)} total projections.")


@cli.command()
@click.option('--player-id', required=True, help='NFL player ID')
@click.option('--scoring', '-s', default='ppr',
              type=click.Choice(['standard', 'ppr', 'half_ppr']),
              help='Fantasy scoring system')
@click.option('--week', '-w', type=int, help='Week for weekly projection')
@click.option('--season', '-y', type=int, help='Target season')
@click.option('--type', '-t', default='both',
              type=click.Choice(['weekly', 'seasonal', 'both']),
              help='Projection type')
def player(player_id, scoring, week, season, type):
    """Get detailed projection for a specific player."""
    click.echo(f"Getting projections for player {player_id}...")
    
    # Initialize engine
    engine = ProjectionEngine(scoring_system=scoring)
    
    try:
        if type in ['weekly', 'both']:
            if week is None:
                click.echo("Week is required for weekly projections", err=True)
                return
            
            weekly_proj = engine.get_player_projection(
                player_id=player_id,
                projection_type='weekly',
                week=week,
                season=season
            )
            
            click.echo(f"\nWeekly Projection (Week {week}):")
            click.echo("=" * 40)
            click.echo(f"Player: {weekly_proj['player_name']} ({weekly_proj['position']}, {weekly_proj['team']})")
            click.echo(f"Projected Points: {weekly_proj['projected_points']}")
            click.echo(f"Confidence Interval: {weekly_proj['confidence_lower']:.1f} - {weekly_proj['confidence_upper']:.1f}")
        
        if type in ['seasonal', 'both']:
            seasonal_proj = engine.get_player_projection(
                player_id=player_id,
                projection_type='seasonal',
                season=season
            )
            
            click.echo(f"\nSeasonal Projection:")
            click.echo("=" * 40)
            click.echo(f"Player: {seasonal_proj['player_name']} ({seasonal_proj['position']}, {seasonal_proj['team']})")
            click.echo(f"Projected Points: {seasonal_proj['projected_points']}")
            click.echo(f"Confidence Interval: {seasonal_proj['confidence_lower']:.1f} - {seasonal_proj['confidence_upper']:.1f}")
            click.echo(f"Expected Games: {seasonal_proj['expected_games']:.1f}")
    
    except Exception as e:
        click.echo(f"Error generating projection: {e}", err=True)


@cli.command()
def test():
    """Test the system with sample data."""
    click.echo("Testing Fantasy Football Valuation Engine...")
    
    try:
        # Initialize engine
        engine = ProjectionEngine(scoring_system='ppr')
        
        click.echo("✓ Engine initialized successfully")
        
        # Try to fit models (this will download data)
        click.echo("Downloading and preparing training data...")
        engine.fit()
        
        click.echo("✓ Models trained successfully")
        click.echo("✓ System test completed successfully!")
        
    except Exception as e:
        click.echo(f"✗ System test failed: {e}", err=True)


if __name__ == '__main__':
    cli()

